import json
import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from django.db.models import Q, Sum, Avg, Count
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from accounts.decorators import workshop_required
from accounts.models import UserProfile, Complaint
from .models import Workshop
from .forms import WorkshopProfileForm, WorkshopRepairEstimateForm, WorkshopRepairBillForm
from services.models import ServiceRequest, RepairEstimate, ServiceRecord, RepairBill, ServiceFeedback


def get_workshop_for_user(user):
    """Retrieve or safely create the Workshop entity associated with the authenticated workshop user."""
    workshop = user.workshops.first()
    if not workshop:
        workshop, _ = Workshop.objects.get_or_create(
            owner=user,
            defaults={
                'workshop_name': f"{user.get_full_name() or user.username}'s Workshop & Service Centre",
                'description': 'Automotive repair and maintenance service facility.',
                'address': getattr(user, 'profile', None).address if hasattr(user, 'profile') and user.profile.address else 'Address pending update',
                'phone_number': getattr(user, 'profile', None).phone_number if hasattr(user, 'profile') and user.profile.phone_number else '',
                'services_offered': 'General Vehicle Servicing, Diagnostics, Engine Repair, Brake System Maintenance',
                'verification_status': Workshop.VerificationStatus.PENDING,
            }
        )
    return workshop


# -------------------------------------------------------------
# 1. Workshop Dashboard Overview & Verification
# -------------------------------------------------------------

@workshop_required
def workshop_dashboard(request):
    """
    Main Workshop Dashboard displaying live database aggregates, active repair bays,
    verification status warnings, and recent incoming requests.
    """
    workshop = get_workshop_for_user(request.user)

    # 1. Live Database Aggregations
    assigned_requests = workshop.assigned_service_requests.all()
    total_requests = assigned_requests.count()
    pending_requests = assigned_requests.filter(status=ServiceRequest.Status.PENDING).count()
    accepted_requests = assigned_requests.filter(status=ServiceRequest.Status.ACCEPTED).count()
    active_repairs = assigned_requests.filter(status=ServiceRequest.Status.IN_PROGRESS).count()
    completed_services = assigned_requests.filter(status=ServiceRequest.Status.COMPLETED).count()

    total_revenue = workshop.get_total_revenue()
    average_rating = workshop.get_average_rating()
    feedbacks_count = workshop.feedbacks.count()

    # Open unassigned incoming requests in the system
    open_incoming_count = ServiceRequest.objects.filter(
        mechanic__isnull=True,
        workshop__isnull=True,
        status=ServiceRequest.Status.PENDING
    ).count()

    # 2. Activity Queues
    recent_requests = ServiceRequest.objects.filter(
        Q(workshop=workshop) | Q(mechanic__isnull=True, workshop__isnull=True),
        status=ServiceRequest.Status.PENDING
    ).select_related('customer', 'vehicle').order_by('-created_at')[:5]

    active_jobs = assigned_requests.filter(
        status__in=[ServiceRequest.Status.ACCEPTED, ServiceRequest.Status.IN_PROGRESS]
    ).select_related('customer', 'vehicle').order_by('-updated_at')[:6]

    recent_completed = assigned_requests.filter(
        status=ServiceRequest.Status.COMPLETED
    ).select_related('customer', 'vehicle', 'bill').order_by('-updated_at')[:5]

    # 3. Monthly Service & Revenue Trend (Past 6 Months)
    today = datetime.date.today()
    monthly_labels = []
    monthly_revenue = []
    monthly_jobs = []

    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        label = datetime.date(year, month, 1).strftime('%b %Y')
        rev_sum = RepairBill.objects.filter(
            provider=request.user,
            service_request__workshop=workshop,
            service_date__year=year,
            service_date__month=month
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        job_count = assigned_requests.filter(
            status=ServiceRequest.Status.COMPLETED,
            updated_at__year=year,
            updated_at__month=month
        ).count()

        monthly_labels.append(label)
        monthly_revenue.append(float(rev_sum))
        monthly_jobs.append(job_count)

    context = {
        'workshop': workshop,
        'page_title': f"{workshop.workshop_name} | Workshop Dashboard",
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'accepted_requests': accepted_requests,
        'active_repairs': active_repairs,
        'completed_services': completed_services,
        'total_revenue': total_revenue,
        'average_rating': average_rating,
        'feedbacks_count': feedbacks_count,
        'open_incoming_count': open_incoming_count,
        'recent_requests': recent_requests,
        'active_jobs': active_jobs,
        'recent_completed': recent_completed,
        'monthly_labels_json': json.dumps(monthly_labels),
        'monthly_revenue_json': json.dumps(monthly_revenue),
        'monthly_jobs_json': json.dumps(monthly_jobs),
    }
    return render(request, 'workshops/dashboard.html', context)


@workshop_required
def verification_status_view(request):
    """Dedicated screen explaining workshop licensing and verification status."""
    workshop = get_workshop_for_user(request.user)
    return render(request, 'workshops/verification_status.html', {
        'workshop': workshop,
        'page_title': 'Verification Status | AutoVia',
    })


# -------------------------------------------------------------
# 2. Workshop Profile Management
# -------------------------------------------------------------

@workshop_required
def workshop_profile(request):
    """View and update workshop business details, services offered, and image."""
    workshop = get_workshop_for_user(request.user)

    if request.method == 'POST':
        form = WorkshopProfileForm(request.POST, request.FILES, instance=workshop)
        if form.is_valid():
            # Save workshop without altering verification status
            ws = form.save(commit=False)
            ws.owner = request.user
            # Ensure verification_status is preserved exactly as in DB
            ws.verification_status = workshop.verification_status
            ws.save()

            messages.success(request, "Workshop profile details have been updated successfully.")
            return redirect('workshops:profile')
        else:
            messages.error(request, "Please correct the form errors indicated below.")
    else:
        form = WorkshopProfileForm(instance=workshop)

    return render(request, 'workshops/profile.html', {
        'workshop': workshop,
        'form': form,
        'page_title': 'Workshop Profile | AutoVia',
    })


# -------------------------------------------------------------
# 3. Service Request Management
# -------------------------------------------------------------

@workshop_required
def incoming_requests(request):
    """
    Display service requests targeted directly to this workshop as well as
    unassigned open requests in the system.
    """
    workshop = get_workshop_for_user(request.user)

    query = request.GET.get('q', '').strip()
    fuel_filter = request.GET.get('fuel', '').strip()
    status_filter = request.GET.get('status', 'PENDING').strip()

    # Requests specifically assigned to this workshop OR unassigned open requests
    requests_qs = ServiceRequest.objects.filter(
        Q(workshop=workshop) | Q(workshop__isnull=True, mechanic__isnull=True)
    )

    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)

    if query:
        requests_qs = requests_qs.filter(
            Q(vehicle__registration_number__icontains=query) |
            Q(vehicle__manufacturer__icontains=query) |
            Q(vehicle__model_name__icontains=query) |
            Q(customer__first_name__icontains=query) |
            Q(customer__last_name__icontains=query) |
            Q(customer__username__icontains=query) |
            Q(problem_description__icontains=query)
        )

    if fuel_filter:
        requests_qs = requests_qs.filter(vehicle__fuel_type=fuel_filter)

    requests_qs = requests_qs.select_related('customer', 'vehicle').order_by('-created_at')

    return render(request, 'workshops/incoming_requests.html', {
        'workshop': workshop,
        'requests': requests_qs,
        'query': query,
        'fuel_filter': fuel_filter,
        'status_filter': status_filter,
        'page_title': 'Incoming Service Requests | AutoVia',
    })


@workshop_required
def workshop_request_detail(request, pk):
    """Inspect full service request ticket, vehicle specs, customer info, quotes, and bills."""
    workshop = get_workshop_for_user(request.user)

    # Allowed if targeted to workshop, already accepted by workshop, or open unassigned
    service_request = get_object_or_404(
        ServiceRequest.objects.select_related('customer', 'vehicle', 'workshop'),
        Q(workshop=workshop) | Q(workshop__isnull=True, mechanic__isnull=True),
        pk=pk
    )

    estimates = service_request.estimates.select_related('provider').order_by('-created_at')
    workshop_estimate = estimates.filter(provider=request.user).first()
    bill = getattr(service_request, 'bill', None)
    feedback = getattr(service_request, 'feedback', None)

    return render(request, 'workshops/request_detail.html', {
        'workshop': workshop,
        'service_request': service_request,
        'estimates': estimates,
        'workshop_estimate': workshop_estimate,
        'bill': bill,
        'feedback': feedback,
        'page_title': f"Request #{service_request.pk} - {service_request.vehicle.registration_number} | AutoVia",
    })


@workshop_required
@require_POST
def accept_request(request, pk):
    """
    Accept an incoming service request with atomic row-level concurrency lock.
    Only APPROVED / VERIFIED workshops may accept requests.
    """
    workshop = get_workshop_for_user(request.user)

    if not workshop.is_approved:
        messages.error(request, "Only verified and approved workshops are authorized to accept service requests.")
        return redirect('workshops:request_detail', pk=pk)

    with transaction.atomic():
        try:
            req = ServiceRequest.objects.select_for_update().get(pk=pk)
        except ServiceRequest.DoesNotExist:
            messages.error(request, "The requested service ticket does not exist.")
            return redirect('workshops:incoming_requests')

        # Check if already accepted or assigned to another workshop/mechanic
        if req.workshop is not None and req.workshop != workshop:
            messages.error(request, "This request has already been assigned to another workshop.")
            return redirect('workshops:incoming_requests')

        if req.mechanic is not None:
            messages.error(request, "This request is assigned to an individual mechanic.")
            return redirect('workshops:incoming_requests')

        if req.status != ServiceRequest.Status.PENDING:
            messages.warning(request, f"Request #{req.pk} is already {req.get_status_display().lower()} and cannot be accepted.")
            return redirect('workshops:request_detail', pk=req.pk)

        # Assign to workshop and update status
        req.workshop = workshop
        req.status = ServiceRequest.Status.ACCEPTED
        req.save()

    messages.success(request, f"Service Request #{req.pk} has been accepted! You can now prepare a repair quotation or assign to bay.")
    return redirect('workshops:request_detail', pk=req.pk)


@workshop_required
@require_POST
def reject_request(request, pk):
    """Reject an incoming service request targeted to this workshop."""
    workshop = get_workshop_for_user(request.user)

    with transaction.atomic():
        try:
            req = ServiceRequest.objects.select_for_update().get(pk=pk)
        except ServiceRequest.DoesNotExist:
            messages.error(request, "The requested service ticket does not exist.")
            return redirect('workshops:incoming_requests')

        if req.workshop == workshop and req.status in [ServiceRequest.Status.PENDING, ServiceRequest.Status.ACCEPTED]:
            req.status = ServiceRequest.Status.REJECTED
            req.save()
            messages.success(request, f"Service Request #{req.pk} has been rejected.")
        else:
            messages.info(request, "Request rejected or bypassed.")

    return redirect('workshops:incoming_requests')


# -------------------------------------------------------------
# 4. Repair Estimates & Quotations
# -------------------------------------------------------------

@workshop_required
def estimate_list(request):
    """List all repair quotations issued by this workshop."""
    workshop = get_workshop_for_user(request.user)

    estimates = RepairEstimate.objects.filter(
        provider=request.user
    ).select_related('service_request__vehicle', 'service_request__customer').order_by('-created_at')

    return render(request, 'workshops/estimates.html', {
        'workshop': workshop,
        'estimates': estimates,
        'page_title': 'Repair Quotations & Estimates | AutoVia',
    })


@workshop_required
def create_or_edit_estimate(request, pk):
    """
    Prepare or update a formal repair quotation for an assigned service request.
    Only APPROVED workshops may prepare quotations.
    """
    workshop = get_workshop_for_user(request.user)

    if not workshop.is_approved:
        messages.error(request, "Your workshop facility must be approved before you can submit official repair estimates.")
        return redirect('workshops:incoming_requests')

    service_request = get_object_or_404(
        ServiceRequest,
        pk=pk,
        workshop=workshop,
        status__in=[ServiceRequest.Status.ACCEPTED, ServiceRequest.Status.IN_PROGRESS]
    )

    # Check for existing estimate by this provider
    estimate_instance = RepairEstimate.objects.filter(
        service_request=service_request,
        provider=request.user
    ).first()

    if request.method == 'POST':
        form = WorkshopRepairEstimateForm(request.POST, instance=estimate_instance)
        if form.is_valid():
            est = form.save(commit=False)
            est.service_request = service_request
            est.provider = request.user
            est.save()
            messages.success(request, f"Repair estimate of ${est.total_cost:.2f} has been submitted for Request #{service_request.pk}.")
            return redirect('workshops:request_detail', pk=service_request.pk)
        else:
            messages.error(request, "Please check the estimate charges and fields.")
    else:
        form = WorkshopRepairEstimateForm(instance=estimate_instance)

    return render(request, 'workshops/estimate_form.html', {
        'workshop': workshop,
        'service_request': service_request,
        'form': form,
        'estimate_instance': estimate_instance,
        'page_title': f"Repair Estimate - Request #{service_request.pk} | AutoVia",
    })


# -------------------------------------------------------------
# 5. Active Repairs & Bay Progress Management
# -------------------------------------------------------------

@workshop_required
def active_repairs(request):
    """Manage active workshop repair jobs currently in bays."""
    workshop = get_workshop_for_user(request.user)

    repairs = workshop.assigned_service_requests.filter(
        status__in=[ServiceRequest.Status.ACCEPTED, ServiceRequest.Status.IN_PROGRESS]
    ).select_related('customer', 'vehicle').order_by('-updated_at')

    return render(request, 'workshops/active_repairs.html', {
        'workshop': workshop,
        'repairs': repairs,
        'page_title': 'Active Repairs & Service Bays | AutoVia',
    })


@workshop_required
@require_POST
def update_repair_status(request, pk):
    """
    Progressive state machine progression:
    ACCEPTED -> IN_PROGRESS -> COMPLETED (or CANCELLED).
    """
    workshop = get_workshop_for_user(request.user)
    service_request = get_object_or_404(ServiceRequest, pk=pk, workshop=workshop)

    new_status = request.POST.get('status')
    valid = False

    if service_request.status == ServiceRequest.Status.ACCEPTED and new_status == ServiceRequest.Status.IN_PROGRESS:
        valid = True
    elif service_request.status == ServiceRequest.Status.IN_PROGRESS and new_status == ServiceRequest.Status.COMPLETED:
        valid = True
    elif service_request.status == ServiceRequest.Status.ACCEPTED and new_status == ServiceRequest.Status.CANCELLED:
        valid = True

    if valid:
        service_request.status = new_status
        service_request.save()
        messages.success(request, f"Service Request #{service_request.pk} status updated to: {service_request.get_status_display()}.")
    else:
        messages.error(request, f"Invalid status transition from {service_request.get_status_display()} to {new_status}.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'workshops:active_repairs'
    return redirect(next_url)


# -------------------------------------------------------------
# 6. Repair Billing & Service History
# -------------------------------------------------------------

@workshop_required
def generate_bill(request, pk):
    """
    Generate an official repair bill for an assigned service request.
    Automatically calculates final charges, updates ServiceRecord,
    and transitions request status to COMPLETED.
    """
    workshop = get_workshop_for_user(request.user)

    if not workshop.is_approved:
        messages.error(request, "Workshop approval is required to issue official repair bills.")
        return redirect('workshops:request_detail', pk=pk)

    service_request = get_object_or_404(ServiceRequest, pk=pk, workshop=workshop)
    existing_bill = getattr(service_request, 'bill', None)

    if request.method == 'POST':
        form = WorkshopRepairBillForm(request.POST, instance=existing_bill)
        if form.is_valid():
            with transaction.atomic():
                bill = form.save(commit=False)
                bill.service_request = service_request
                bill.provider = request.user
                bill.customer = service_request.customer
                bill.vehicle = service_request.vehicle
                bill.save()

                # Sync immutable ServiceRecord so vehicle owner has verified history
                ServiceRecord.objects.update_or_create(
                    service_request=service_request,
                    defaults={
                        'vehicle': service_request.vehicle,
                        'service_description': bill.service_description,
                        'service_date': bill.service_date,
                        'odometer_reading': service_request.vehicle.current_odometer,
                        'total_cost': bill.total_amount,
                    }
                )

                # Transition ServiceRequest to COMPLETED
                if service_request.status != ServiceRequest.Status.COMPLETED:
                    service_request.status = ServiceRequest.Status.COMPLETED
                    service_request.save()

            messages.success(request, f"Official Repair Bill #{bill.pk} for ${bill.total_amount:.2f} issued successfully.")
            return redirect('workshops:bill_detail', pk=bill.pk)
    else:
        # Pre-populate estimate amounts if available and no bill exists yet
        initial = {
            'service_description': service_request.problem_description,
            'service_date': datetime.date.today(),
        }
        estimate = service_request.estimates.filter(provider=request.user).first()
        if estimate and not existing_bill:
            initial['labor_charges'] = estimate.labor_cost
            initial['parts_charges'] = estimate.parts_cost
            initial['additional_charges'] = estimate.additional_cost
            if estimate.description:
                initial['service_description'] = estimate.description

        form = WorkshopRepairBillForm(instance=existing_bill, initial=initial)

    return render(request, 'workshops/bill_form.html', {
        'workshop': workshop,
        'service_request': service_request,
        'form': form,
        'existing_bill': existing_bill,
        'page_title': f"Generate Bill - Request #{service_request.pk} | AutoVia",
    })


@workshop_required
def bill_detail(request, pk):
    """Display official printable repair invoice."""
    workshop = get_workshop_for_user(request.user)
    bill = get_object_or_404(RepairBill, pk=pk, provider=request.user)

    return render(request, 'workshops/bill_detail.html', {
        'workshop': workshop,
        'bill': bill,
        'service_request': bill.service_request,
        'page_title': f"Repair Invoice #{bill.pk} | AutoVia",
    })


@workshop_required
def service_history(request):
    """View completed service records and repair invoices for this workshop."""
    workshop = get_workshop_for_user(request.user)

    completed_jobs = workshop.assigned_service_requests.filter(
        status=ServiceRequest.Status.COMPLETED
    ).select_related('customer', 'vehicle', 'bill').order_by('-updated_at')

    total_revenue = workshop.get_total_revenue()

    return render(request, 'workshops/service_history.html', {
        'workshop': workshop,
        'completed_jobs': completed_jobs,
        'total_revenue': total_revenue,
        'page_title': 'Workshop Service History | AutoVia',
    })


# -------------------------------------------------------------
# 7. Customer Feedback & Ratings
# -------------------------------------------------------------

@workshop_required
def customer_feedback(request):
    """Display customer reviews and ratings for this workshop."""
    workshop = get_workshop_for_user(request.user)

    feedbacks = ServiceFeedback.objects.filter(
        workshop=workshop
    ).select_related('customer', 'service_request__vehicle').order_by('-created_at')

    avg_rating = workshop.get_average_rating()
    total_reviews = feedbacks.count()

    # Rating distribution breakdown
    rating_counts = {i: feedbacks.filter(rating=i).count() for i in range(5, 0, -1)}

    return render(request, 'workshops/feedback.html', {
        'workshop': workshop,
        'feedbacks': feedbacks,
        'avg_rating': avg_rating,
        'total_reviews': total_reviews,
        'rating_counts': rating_counts,
        'page_title': 'Customer Reviews & Feedback | AutoVia',
    })


# -------------------------------------------------------------
# 8. Business Analytics
# -------------------------------------------------------------

@workshop_required
def business_analytics(request):
    """
    Comprehensive business analytics dashboard with Chart.js:
    Monthly revenue, job completion rates, and service category breakdown.
    """
    workshop = get_workshop_for_user(request.user)
    assigned_requests = workshop.assigned_service_requests.all()

    total_jobs = assigned_requests.count()
    completed_jobs = assigned_requests.filter(status=ServiceRequest.Status.COMPLETED).count()
    pending_jobs = assigned_requests.filter(status=ServiceRequest.Status.PENDING).count()
    in_progress_jobs = assigned_requests.filter(status=ServiceRequest.Status.IN_PROGRESS).count()
    cancelled_jobs = assigned_requests.filter(status__in=[ServiceRequest.Status.CANCELLED, ServiceRequest.Status.REJECTED]).count()

    completion_rate = round((completed_jobs / total_jobs * 100), 1) if total_jobs > 0 else 0.0
    total_revenue = workshop.get_total_revenue()
    avg_ticket_value = round((total_revenue / completed_jobs), 2) if completed_jobs > 0 else Decimal('0.00')

    # 1. Monthly Revenue & Volume Trends (Last 6 Months)
    today = datetime.date.today()
    monthly_labels = []
    monthly_revenue = []
    monthly_job_counts = []

    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        label = datetime.date(year, month, 1).strftime('%b %Y')
        rev = RepairBill.objects.filter(
            provider=request.user,
            service_request__workshop=workshop,
            service_date__year=year,
            service_date__month=month
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        count = assigned_requests.filter(
            status=ServiceRequest.Status.COMPLETED,
            updated_at__year=year,
            updated_at__month=month
        ).count()

        monthly_labels.append(label)
        monthly_revenue.append(float(rev))
        monthly_job_counts.append(count)

    # 2. Fuel Type Breakdown of Serviced Vehicles
    fuel_breakdown = assigned_requests.values('vehicle__fuel_type').annotate(count=Count('id')).order_by('-count')
    fuel_labels = [item['vehicle__fuel_type'] or 'Unknown' for item in fuel_breakdown]
    fuel_data = [item['count'] for item in fuel_breakdown]

    context = {
        'workshop': workshop,
        'page_title': 'Business Analytics & Performance | AutoVia',
        'total_jobs': total_jobs,
        'completed_jobs': completed_jobs,
        'pending_jobs': pending_jobs,
        'in_progress_jobs': in_progress_jobs,
        'cancelled_jobs': cancelled_jobs,
        'completion_rate': completion_rate,
        'total_revenue': total_revenue,
        'avg_ticket_value': avg_ticket_value,
        'monthly_labels_json': json.dumps(monthly_labels),
        'monthly_revenue_json': json.dumps(monthly_revenue),
        'monthly_job_counts_json': json.dumps(monthly_job_counts),
        'fuel_labels_json': json.dumps(fuel_labels),
        'fuel_data_json': json.dumps(fuel_data),
    }
    return render(request, 'workshops/analytics.html', context)
