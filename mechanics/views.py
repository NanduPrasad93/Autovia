from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Q, Sum, Avg
from django.utils import timezone
from decimal import Decimal
import datetime

from accounts.decorators import mechanic_required, vehicle_owner_required
from accounts.models import UserProfile
from .models import MechanicProfile
from .forms import MechanicProfileForm, RepairEstimateForm, RepairBillForm
from services.models import ServiceRequest, RepairEstimate, RepairBill, ServiceRecord, ServiceFeedback


# -------------------------------------------------------------
# 1. Mechanic Dashboard Overview
# -------------------------------------------------------------

@mechanic_required
def mechanic_dashboard(request):
    """
    Main console for authenticated mechanics displaying actual database KPIs,
    availability status, incoming requests, active repairs, and financial revenue.
    """
    mechanic, _ = MechanicProfile.objects.get_or_create(user=request.user)

    # 1. Incoming Requests available for acceptance (Assigned to this mechanic OR unassigned open pool)
    incoming_query = ServiceRequest.objects.filter(
        Q(mechanic=mechanic) | Q(mechanic__isnull=True, workshop__isnull=True),
        status=ServiceRequest.Status.PENDING
    )
    total_incoming_requests = incoming_query.count()

    # 2. Specific Pending Requests assigned to this mechanic
    pending_assigned_count = ServiceRequest.objects.filter(
        mechanic=mechanic,
        status=ServiceRequest.Status.PENDING
    ).count()

    # 3. Accepted Requests
    accepted_count = ServiceRequest.objects.filter(
        mechanic=mechanic,
        status=ServiceRequest.Status.ACCEPTED
    ).count()

    # 4. Active Repairs (In Progress)
    active_repairs_count = ServiceRequest.objects.filter(
        mechanic=mechanic,
        status=ServiceRequest.Status.IN_PROGRESS
    ).count()

    # 5. Completed Repairs
    completed_repairs_count = ServiceRequest.objects.filter(
        mechanic=mechanic,
        status=ServiceRequest.Status.COMPLETED
    ).count()

    # 6. Total Repair Earnings (Sum of all completed RepairBills issued by this mechanic)
    total_earnings = RepairBill.objects.filter(
        provider=request.user
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # 7. Customer Ratings & Reviews
    feedbacks = ServiceFeedback.objects.filter(mechanic=mechanic)
    total_reviews = feedbacks.count()
    avg_rating = feedbacks.aggregate(avg=Avg('rating'))['avg'] or 0.0

    # Recent Data Streams
    recent_requests = incoming_query.select_related('customer', 'vehicle').order_by('-created_at')[:5]
    active_jobs = ServiceRequest.objects.filter(
        mechanic=mechanic,
        status__in=[ServiceRequest.Status.ACCEPTED, ServiceRequest.Status.IN_PROGRESS]
    ).select_related('customer', 'vehicle').order_by('-updated_at')[:5]
    recent_feedbacks = feedbacks.select_related('customer', 'service_request__vehicle').order_by('-created_at')[:3]

    context = {
        'mechanic': mechanic,
        'total_incoming_requests': total_incoming_requests,
        'pending_assigned_count': pending_assigned_count,
        'accepted_count': accepted_count,
        'active_repairs_count': active_repairs_count,
        'completed_repairs_count': completed_repairs_count,
        'total_earnings': total_earnings,
        'avg_rating': round(avg_rating, 1),
        'total_reviews': total_reviews,
        'recent_requests': recent_requests,
        'active_jobs': active_jobs,
        'recent_feedbacks': recent_feedbacks,
        'page_title': 'Mechanic Console | AutoVia',
    }
    return render(request, 'mechanics/dashboard.html', context)


# -------------------------------------------------------------
# 2. Mechanic Profile Management
# -------------------------------------------------------------

@mechanic_required
def mechanic_profile_edit(request):
    """
    Allow mechanics to view and update credentials, specialization, experience,
    service location, description, and profile avatar.
    Verification status is protected and cannot be changed by the mechanic.
    """
    mechanic, _ = MechanicProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = MechanicProfileForm(request.POST, request.FILES, instance=mechanic, user=request.user)
        if form.is_valid():
            # Save mechanic model fields (verification_status is excluded and intact)
            saved_mechanic = form.save()

            # Update User & UserProfile
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()

            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.phone_number = form.cleaned_data.get('phone_number', '')
            if 'profile_image' in request.FILES:
                profile.profile_image = request.FILES['profile_image']
            profile.save()

            messages.success(request, "Your technician profile has been updated successfully.")
            return redirect('mechanics:profile')
    else:
        form = MechanicProfileForm(instance=mechanic, user=request.user)

    return render(request, 'mechanics/profile.html', {
        'form': form,
        'mechanic': mechanic,
        'page_title': 'My Professional Profile | AutoVia',
    })


# -------------------------------------------------------------
# 3. Availability Toggle & Settings
# -------------------------------------------------------------

@mechanic_required
def availability_view(request):
    """Dedicated screen to review and manage technician availability."""
    mechanic, _ = MechanicProfile.objects.get_or_create(user=request.user)
    return render(request, 'mechanics/availability.html', {
        'mechanic': mechanic,
        'page_title': 'Availability Settings | AutoVia',
    })


@mechanic_required
@require_POST
def toggle_availability(request):
    """Toggle real-time dispatch availability status."""
    mechanic, _ = MechanicProfile.objects.get_or_create(user=request.user)
    mechanic.is_available = not mechanic.is_available
    mechanic.save()

    status_name = "Available (Active for service dispatches)" if mechanic.is_available else "Unavailable (Off-duty)"
    messages.success(request, f"Your availability status has been updated to: {status_name}.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'mechanics:dashboard'
    return redirect(next_url)


# -------------------------------------------------------------
# 4. Service Request Management (Incoming, Detail, Accept, Reject)
# -------------------------------------------------------------

@mechanic_required
def incoming_requests(request):
    """
    Display pending service requests available for the mechanic to accept.
    Includes requests specifically targeted to this mechanic and unassigned pool requests.
    """
    mechanic, _ = MechanicProfile.objects.get_or_create(user=request.user)
    query = request.GET.get('q', '').strip()

    requests_qs = ServiceRequest.objects.filter(
        Q(mechanic=mechanic) | Q(mechanic__isnull=True, workshop__isnull=True),
        status=ServiceRequest.Status.PENDING
    ).select_related('customer', 'vehicle')

    if query:
        requests_qs = requests_qs.filter(
            Q(vehicle__manufacturer__icontains=query) |
            Q(vehicle__model_name__icontains=query) |
            Q(vehicle__registration_number__icontains=query) |
            Q(problem_description__icontains=query)
        )

    requests_qs = requests_qs.order_by('-created_at')

    return render(request, 'mechanics/incoming_requests.html', {
        'requests': requests_qs,
        'mechanic': mechanic,
        'query': query,
        'page_title': 'Incoming Service Requests | AutoVia',
    })


@mechanic_required
def mechanic_request_detail(request, pk):
    """
    Detailed inspection of a service request.
    Only accessible if assigned to this mechanic or unassigned PENDING.
    """
    mechanic, _ = MechanicProfile.objects.get_or_create(user=request.user)

    service_request = get_object_or_404(
        ServiceRequest.objects.select_related('customer', 'vehicle'),
        pk=pk
    )

    # Security check: verify this mechanic is allowed to view this request
    is_assigned = (service_request.mechanic == mechanic)
    is_unassigned_pending = (service_request.mechanic is None and service_request.workshop is None and service_request.status == ServiceRequest.Status.PENDING)

    if not (is_assigned or is_unassigned_pending):
        messages.error(request, "Access Denied: You do not have permission to view this service ticket.")
        return redirect('mechanics:dashboard')

    estimates = service_request.estimates.all().order_by('-created_at')
    my_estimate = estimates.filter(provider=request.user).first()
    bill = getattr(service_request, 'bill', None)
    feedback = getattr(service_request, 'feedback', None)

    return render(request, 'mechanics/request_detail.html', {
        'service_request': service_request,
        'mechanic': mechanic,
        'estimates': estimates,
        'my_estimate': my_estimate,
        'bill': bill,
        'feedback': feedback,
        'page_title': f"Request #{service_request.pk} Details | AutoVia",
    })


@mechanic_required
@require_POST
def accept_request(request, pk):
    """
    Accept an incoming service request with row-level locking to prevent race conditions.
    Enforces mechanic verification and active availability.
    """
    mechanic, _ = MechanicProfile.objects.get_or_create(user=request.user)

    # 1. Verification requirement
    if mechanic.verification_status != MechanicProfile.VerificationStatus.VERIFIED:
        messages.error(request, "Your mechanic credentials are currently pending admin verification. You cannot accept service requests until verified.")
        return redirect('mechanics:request_detail', pk=pk)

    # 2. Availability requirement
    if not mechanic.is_available:
        messages.warning(request, "You are currently marked as Unavailable. Please set your status to Available before accepting service tickets.")
        return redirect('mechanics:request_detail', pk=pk)

    # 3. Transactional atomic lock
    with transaction.atomic():
        try:
            req = ServiceRequest.objects.select_for_update().get(pk=pk)
        except ServiceRequest.DoesNotExist:
            messages.error(request, "The requested service ticket does not exist.")
            return redirect('mechanics:incoming_requests')

        # Check status
        if req.status != ServiceRequest.Status.PENDING:
            messages.error(request, f"This request is currently {req.get_status_display().lower()} and can no longer be accepted.")
            return redirect('mechanics:incoming_requests')

        # Check provider assignment conflict
        if req.mechanic and req.mechanic != mechanic:
            messages.error(request, "This request has already been assigned to another mechanic.")
            return redirect('mechanics:incoming_requests')

        if req.workshop:
            messages.error(request, "This request is assigned to a workshop facility.")
            return redirect('mechanics:incoming_requests')

        # Assign and accept
        req.mechanic = mechanic
        req.status = ServiceRequest.Status.ACCEPTED
        req.save()

    messages.success(request, f"Service Request #{req.pk} accepted! You may now prepare a repair estimate or begin diagnostics.")
    return redirect('mechanics:request_detail', pk=req.pk)


@mechanic_required
@require_POST
def reject_request(request, pk):
    """Reject an incoming service request."""
    mechanic, _ = MechanicProfile.objects.get_or_create(user=request.user)

    with transaction.atomic():
        try:
            req = ServiceRequest.objects.select_for_update().get(pk=pk)
        except ServiceRequest.DoesNotExist:
            messages.error(request, "The requested service ticket does not exist.")
            return redirect('mechanics:incoming_requests')

        if req.mechanic == mechanic and req.status in [ServiceRequest.Status.PENDING, ServiceRequest.Status.ACCEPTED]:
            req.status = ServiceRequest.Status.REJECTED
            req.save()
            messages.success(request, f"Service Request #{req.pk} has been rejected.")
        else:
            messages.info(request, "Service request passed.")

    return redirect('mechanics:incoming_requests')


# -------------------------------------------------------------
# 5. Repair Estimates
# -------------------------------------------------------------

@mechanic_required
def estimate_list(request):
    """List all repair estimates submitted by this mechanic."""
    estimates = RepairEstimate.objects.filter(
        provider=request.user
    ).select_related('service_request__vehicle', 'service_request__customer').order_by('-created_at')

    return render(request, 'mechanics/estimates.html', {
        'estimates': estimates,
        'page_title': 'Repair Estimates | AutoVia',
    })


@mechanic_required
def create_or_edit_estimate(request, pk):
    """Prepare or update a formal repair cost estimate for an assigned service request."""
    mechanic, _ = MechanicProfile.objects.get_or_create(user=request.user)

    if mechanic.verification_status != MechanicProfile.VerificationStatus.VERIFIED:
        messages.error(request, "Account verification required to author repair estimates.")
        return redirect('mechanics:request_detail', pk=pk)

    service_request = get_object_or_404(ServiceRequest, pk=pk, mechanic=mechanic)
    estimate = RepairEstimate.objects.filter(service_request=service_request, provider=request.user).first()

    if request.method == 'POST':
        form = RepairEstimateForm(request.POST, instance=estimate)
        if form.is_valid():
            est = form.save(commit=False)
            est.service_request = service_request
            est.provider = request.user
            est.save()
            messages.success(request, f"Repair estimate for ${est.total_cost} saved and shared with the vehicle owner.")
            return redirect('mechanics:request_detail', pk=service_request.pk)
    else:
        form = RepairEstimateForm(instance=estimate)

    return render(request, 'mechanics/estimate_form.html', {
        'form': form,
        'service_request': service_request,
        'estimate': estimate,
        'is_edit': bool(estimate),
        'page_title': f"Prepare Estimate - Request #{service_request.pk} | AutoVia",
    })


# -------------------------------------------------------------
# 6. Active Repairs & Status Milestones
# -------------------------------------------------------------

@mechanic_required
def active_repairs(request):
    """View and update ongoing repair jobs assigned to this technician."""
    mechanic, _ = MechanicProfile.objects.get_or_create(user=request.user)

    active_jobs = ServiceRequest.objects.filter(
        mechanic=mechanic,
        status__in=[ServiceRequest.Status.ACCEPTED, ServiceRequest.Status.IN_PROGRESS]
    ).select_related('customer', 'vehicle').order_by('-updated_at')

    return render(request, 'mechanics/active_repairs.html', {
        'active_jobs': active_jobs,
        'mechanic': mechanic,
        'page_title': 'Active Repairs & Work Orders | AutoVia',
    })


@mechanic_required
@require_POST
def update_repair_status(request, pk):
    """
    Advance service status through progressive milestones:
    ACCEPTED -> IN_PROGRESS -> COMPLETED.
    Rejects invalid backwards or illegal transitions.
    """
    mechanic, _ = MechanicProfile.objects.get_or_create(user=request.user)
    service_request = get_object_or_404(ServiceRequest, pk=pk, mechanic=mechanic)

    new_status = request.POST.get('status')
    valid = False

    # Valid State Transition Matrix
    if service_request.status == ServiceRequest.Status.ACCEPTED and new_status == ServiceRequest.Status.IN_PROGRESS:
        valid = True
    elif service_request.status == ServiceRequest.Status.IN_PROGRESS and new_status == ServiceRequest.Status.COMPLETED:
        valid = True
    elif service_request.status == ServiceRequest.Status.ACCEPTED and new_status == ServiceRequest.Status.CANCELLED:
        valid = True

    if valid:
        service_request.status = new_status
        service_request.save()
        messages.success(request, f"Repair order #{service_request.pk} status updated to: {service_request.get_status_display()}.")
    else:
        messages.error(request, f"Invalid status transition from {service_request.get_status_display()} to {new_status}.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'mechanics:active_repairs'
    return redirect(next_url)


# -------------------------------------------------------------
# 7. Repair Bills (Invoicing)
# -------------------------------------------------------------

@mechanic_required
def generate_bill(request, pk):
    """
    Generate an official repair bill for an assigned service request.
    Automatically calculates final charges, creates/updates ServiceRecord,
    and updates request status to COMPLETED.
    """
    mechanic, _ = MechanicProfile.objects.get_or_create(user=request.user)

    if mechanic.verification_status != MechanicProfile.VerificationStatus.VERIFIED:
        messages.error(request, "Account verification required to issue repair invoices.")
        return redirect('mechanics:request_detail', pk=pk)

    service_request = get_object_or_404(ServiceRequest, pk=pk, mechanic=mechanic)
    existing_bill = getattr(service_request, 'bill', None)

    if request.method == 'POST':
        form = RepairBillForm(request.POST, instance=existing_bill)
        if form.is_valid():
            with transaction.atomic():
                bill = form.save(commit=False)
                bill.service_request = service_request
                bill.provider = request.user
                bill.customer = service_request.customer
                bill.vehicle = service_request.vehicle
                bill.save()

                # Sync into ServiceRecord so vehicle owner has verified history
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

            messages.success(request, f"Repair Bill #{bill.pk} for ${bill.total_amount} issued successfully.")
            return redirect('mechanics:bill_detail', pk=bill.pk)
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

        form = RepairBillForm(instance=existing_bill, initial=initial if not existing_bill else None)

    return render(request, 'mechanics/bill_form.html', {
        'form': form,
        'service_request': service_request,
        'existing_bill': existing_bill,
        'page_title': f"Generate Bill - Request #{service_request.pk} | AutoVia",
    })


@mechanic_required
def bill_list(request):
    """View all finalized bills issued by this mechanic with financial aggregates."""
    bills = RepairBill.objects.filter(
        provider=request.user
    ).select_related('service_request__vehicle', 'customer').order_by('-service_date', '-created_at')

    total_earned = bills.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    paid_count = bills.filter(is_paid=True).count()
    unpaid_count = bills.filter(is_paid=False).count()

    return render(request, 'mechanics/bills.html', {
        'bills': bills,
        'total_earned': total_earned,
        'paid_count': paid_count,
        'unpaid_count': unpaid_count,
        'page_title': 'Billing & Invoices | AutoVia',
    })


@mechanic_required
def bill_detail(request, pk):
    """Printable / itemized final repair invoice view."""
    bill = get_object_or_404(
        RepairBill.objects.select_related('service_request__vehicle', 'customer', 'provider'),
        pk=pk,
        provider=request.user
    )

    return render(request, 'mechanics/bill_detail.html', {
        'bill': bill,
        'page_title': f"Invoice #{bill.pk} | AutoVia",
    })


# -------------------------------------------------------------
# 8. Customer Feedback & Ratings
# -------------------------------------------------------------

@mechanic_required
def feedback_list(request):
    """Display ratings, performance score, and customer testimonials."""
    mechanic, _ = MechanicProfile.objects.get_or_create(user=request.user)

    feedbacks = ServiceFeedback.objects.filter(
        mechanic=mechanic
    ).select_related('customer', 'service_request__vehicle').order_by('-created_at')

    total_count = feedbacks.count()
    avg_score = feedbacks.aggregate(avg=Avg('rating'))['avg'] or 0.0

    return render(request, 'mechanics/feedback.html', {
        'feedbacks': feedbacks,
        'mechanic': mechanic,
        'total_count': total_count,
        'avg_score': round(avg_score, 1),
        'page_title': 'Customer Feedback & Reviews | AutoVia',
    })


# -------------------------------------------------------------
# 9. Public / Customer Facing Directory Views (Preserved)
# -------------------------------------------------------------

@vehicle_owner_required
def mechanic_list(request):
    """Customer directory to search verified technicians."""
    query = request.GET.get('q', '').strip()
    specialization = request.GET.get('specialization', '').strip()

    mechanics = MechanicProfile.objects.all()

    show_all = request.GET.get('show_all', 'false') == 'true'
    if not show_all:
        mechanics = mechanics.filter(verification_status=MechanicProfile.VerificationStatus.VERIFIED)

    if query:
        mechanics = mechanics.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__username__icontains=query) |
            Q(specialization__icontains=query) |
            Q(service_location__icontains=query)
        )

    if specialization:
        mechanics = mechanics.filter(specialization__icontains=specialization)

    mechanics = mechanics.order_by('-is_available', '-experience_years')

    return render(request, 'mechanics/mechanic_list.html', {
        'mechanics': mechanics,
        'query': query,
        'specialization': specialization,
        'show_all': show_all,
        'page_title': 'Find Verified Mechanics | AutoVia',
    })


@vehicle_owner_required
def mechanic_detail(request, pk):
    """Customer view of a technician profile."""
    mechanic = get_object_or_404(MechanicProfile, pk=pk)
    user_vehicles = request.user.vehicles.all()

    return render(request, 'mechanics/mechanic_detail.html', {
        'mechanic': mechanic,
        'user_vehicles': user_vehicles,
        'page_title': f"Mechanic: {mechanic.user.get_full_name() or mechanic.user.username} | AutoVia",
    })
