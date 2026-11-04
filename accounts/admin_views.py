import json
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.paginator import Paginator

from accounts.decorators import admin_required
from accounts.models import UserProfile, Complaint, ActivityLog, log_activity
from mechanics.models import MechanicProfile
from workshops.models import Workshop
from suppliers.models import SupplierProfile, SparePart
from services.models import ServiceRequest, RepairEstimate, RepairBill, ServiceFeedback
from vehicles.models import Vehicle


# -------------------------------------------------------------
# 1. Admin Dashboard Overview
# -------------------------------------------------------------

@admin_required
def admin_dashboard_overview(request):
    """
    Central administrative dashboard overview displaying real database analytics,
    provider verification queues, open complaints, and recent platform events.
    """
    # 1. User & Role Counts
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    total_vehicle_owners = UserProfile.objects.filter(role=UserProfile.Role.VEHICLE_OWNER).count()
    total_mechanics = UserProfile.objects.filter(role=UserProfile.Role.MECHANIC).count()
    total_workshops = UserProfile.objects.filter(role=UserProfile.Role.WORKSHOP).count()
    total_suppliers = UserProfile.objects.filter(role=UserProfile.Role.SUPPLIER).count()
    total_admins = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).distinct().count()

    # 2. Provider Verification Pipeline
    pending_mechanic_verifications = MechanicProfile.objects.filter(
        verification_status=MechanicProfile.VerificationStatus.PENDING
    ).count()

    pending_workshop_approvals = Workshop.objects.filter(
        verification_status=Workshop.VerificationStatus.PENDING
    ).count()

    pending_supplier_verifications = SupplierProfile.objects.filter(
        verification_status=SupplierProfile.VerificationStatus.PENDING
    ).count()

    total_pending_verifications = (
        pending_mechanic_verifications +
        pending_workshop_approvals +
        pending_supplier_verifications
    )

    # 3. Operations & Governance
    total_service_requests = ServiceRequest.objects.count()
    active_service_requests = ServiceRequest.objects.filter(
        status__in=[ServiceRequest.Status.ACCEPTED, ServiceRequest.Status.IN_PROGRESS]
    ).count()

    total_complaints = Complaint.objects.count()
    open_complaints = Complaint.objects.filter(status=Complaint.Status.OPEN).count()
    unresolved_complaints = Complaint.objects.filter(
        status__in=[Complaint.Status.OPEN, Complaint.Status.IN_PROGRESS]
    ).count()

    # 4. Activity Feeds & Queues
    recent_activities = ActivityLog.objects.select_related('user').order_by('-created_at')[:8]
    recent_users = User.objects.select_related('profile').order_by('-date_joined')[:6]
    pending_mechanics_sample = MechanicProfile.objects.filter(
        verification_status=MechanicProfile.VerificationStatus.PENDING
    ).select_related('user')[:4]
    pending_workshops_sample = Workshop.objects.filter(
        verification_status=Workshop.VerificationStatus.PENDING
    ).select_related('owner')[:4]
    pending_suppliers_sample = SupplierProfile.objects.filter(
        verification_status=SupplierProfile.VerificationStatus.PENDING
    ).select_related('user')[:4]

    # 5. Visual Chart Data (User Role Breakdown)
    role_labels = ['Vehicle Owners', 'Mechanics', 'Workshops', 'Suppliers', 'Administrators']
    role_counts = [
        total_vehicle_owners,
        total_mechanics,
        total_workshops,
        total_suppliers,
        total_admins
    ]

    # Monthly Service Requests (Past 6 Months)
    today = datetime.date.today()
    monthly_labels = []
    monthly_requests_data = []
    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        label = datetime.date(year, month, 1).strftime('%b %Y')
        cnt = ServiceRequest.objects.filter(
            created_at__year=year,
            created_at__month=month
        ).count()
        monthly_labels.append(label)
        monthly_requests_data.append(cnt)

    context = {
        'page_title': 'Administration Portal | AutoVia',
        'total_users': total_users,
        'active_users': active_users,
        'total_vehicle_owners': total_vehicle_owners,
        'total_mechanics': total_mechanics,
        'total_workshops': total_workshops,
        'total_suppliers': total_suppliers,
        'total_admins': total_admins,
        'pending_mechanic_verifications': pending_mechanic_verifications,
        'pending_workshop_approvals': pending_workshop_approvals,
        'pending_supplier_verifications': pending_supplier_verifications,
        'total_pending_verifications': total_pending_verifications,
        'total_service_requests': total_service_requests,
        'active_service_requests': active_service_requests,
        'total_complaints': total_complaints,
        'open_complaints': open_complaints,
        'unresolved_complaints': unresolved_complaints,
        'recent_activities': recent_activities,
        'recent_users': recent_users,
        'pending_mechanics_sample': pending_mechanics_sample,
        'pending_workshops_sample': pending_workshops_sample,
        'pending_suppliers_sample': pending_suppliers_sample,
        'role_labels_json': json.dumps(role_labels),
        'role_counts_json': json.dumps(role_counts),
        'monthly_labels_json': json.dumps(monthly_labels),
        'monthly_requests_json': json.dumps(monthly_requests_data),
    }
    return render(request, 'admin_dashboard/overview.html', context)


# -------------------------------------------------------------
# 2. User Management
# -------------------------------------------------------------

@admin_required
def admin_user_list(request):
    """
    Search, filter, and inspect registered platform accounts.
    Allows toggling active status with safety guards against self-deactivation.
    """
    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '').strip()
    status_filter = request.GET.get('status', '').strip()

    users_qs = User.objects.select_related('profile').order_by('-date_joined')

    if query:
        users_qs = users_qs.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )

    if role_filter:
        users_qs = users_qs.filter(profile__role=role_filter)

    if status_filter == 'active':
        users_qs = users_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        users_qs = users_qs.filter(is_active=False)

    paginator = Paginator(users_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_title': 'User Management | AutoVia Administration',
        'page_obj': page_obj,
        'query': query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'roles': UserProfile.Role.choices,
        'total_filtered': users_qs.count(),
    }
    return render(request, 'admin_dashboard/users.html', context)


@admin_required
def admin_user_detail(request, pk):
    """Deep inspection of a specific user account, role records, and linked entities."""
    user_obj = get_object_or_404(User.objects.select_related('profile'), pk=pk)

    # Related domain models
    vehicles = user_obj.vehicles.all() if hasattr(user_obj, 'vehicles') else []
    service_requests = user_obj.customer_service_requests.all()[:10] if hasattr(user_obj, 'customer_service_requests') else []
    mechanic_profile = getattr(user_obj, 'mechanic_profile', None)
    workshops = user_obj.workshops.all() if hasattr(user_obj, 'workshops') else []
    supplier_profile = getattr(user_obj, 'supplier_profile', None)
    complaints = user_obj.complaints.all()[:5]
    user_activities = ActivityLog.objects.filter(
        Q(user=user_obj) | Q(target_object_id=str(user_obj.pk))
    ).order_by('-created_at')[:10]

    context = {
        'page_title': f"User Profile: {user_obj.username} | AutoVia Admin",
        'target_user': user_obj,
        'vehicles': vehicles,
        'service_requests': service_requests,
        'mechanic_profile': mechanic_profile,
        'workshops': workshops,
        'supplier_profile': supplier_profile,
        'complaints': complaints,
        'user_activities': user_activities,
    }
    return render(request, 'admin_dashboard/user_detail.html', context)


@admin_required
@require_POST
def admin_user_toggle_status(request, pk):
    """
    Safely activate or deactivate user account.
    Blocks self-deactivation and staff altering superusers.
    """
    user_obj = get_object_or_404(User, pk=pk)

    # 1. Prevent self-deactivation
    if user_obj.pk == request.user.pk:
        messages.error(request, "Security Policy: Administrators cannot deactivate their own active user account.")
        return redirect('admin_dashboard:user_detail', pk=pk)

    # 2. Protect superuser accounts from non-superusers
    if user_obj.is_superuser and not request.user.is_superuser:
        messages.error(request, "Security Policy: Only superusers can modify another superuser account.")
        return redirect('admin_dashboard:user_detail', pk=pk)

    new_status = not user_obj.is_active
    user_obj.is_active = new_status
    user_obj.save()

    status_str = "activated" if new_status else "deactivated"
    action_type = ActivityLog.ActionType.USER_STATUS
    description = f"Administrator {request.user.username} {status_str} user account '{user_obj.username}' (ID: {user_obj.pk})."
    log_activity(request.user, action_type, description, target=user_obj)

    messages.success(request, f"User account '{user_obj.username}' has been successfully {status_str}.")
    return redirect('admin_dashboard:user_detail', pk=pk)


# -------------------------------------------------------------
# 3. Mechanic Verification
# -------------------------------------------------------------

@admin_required
def admin_mechanic_list(request):
    """Browse, filter, and audit all mechanic profiles."""
    status_filter = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()

    mechanics = MechanicProfile.objects.select_related('user', 'user__profile').order_by('-created_at')

    if status_filter:
        mechanics = mechanics.filter(verification_status=status_filter)

    if query:
        mechanics = mechanics.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(specialization__icontains=query) |
            Q(service_location__icontains=query)
        )

    context = {
        'page_title': 'Mechanic Verification Management | AutoVia Admin',
        'mechanics': mechanics,
        'status_filter': status_filter,
        'query': query,
        'statuses': MechanicProfile.VerificationStatus.choices,
        'pending_count': MechanicProfile.objects.filter(verification_status=MechanicProfile.VerificationStatus.PENDING).count(),
    }
    return render(request, 'admin_dashboard/mechanics.html', context)


@admin_required
def admin_mechanic_detail_verify(request, pk):
    """Inspect mechanic credentials and execute approval or rejection."""
    mechanic = get_object_or_404(MechanicProfile.objects.select_related('user', 'user__profile'), pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('rejection_reason', '').strip()

        if action == 'approve':
            mechanic.verification_status = MechanicProfile.VerificationStatus.VERIFIED
            mechanic.rejection_reason = ''
            mechanic.save()

            log_activity(
                request.user,
                ActivityLog.ActionType.MECHANIC_VERIFICATION,
                f"Approved mechanic application for '{mechanic.user.get_full_name() or mechanic.user.username}' (Specialization: {mechanic.specialization}).",
                target=mechanic
            )
            messages.success(request, f"Mechanic '{mechanic.user.username}' has been verified and accredited successfully.")

        elif action == 'reject':
            mechanic.verification_status = MechanicProfile.VerificationStatus.REJECTED
            mechanic.rejection_reason = reason
            mechanic.save()

            log_activity(
                request.user,
                ActivityLog.ActionType.MECHANIC_VERIFICATION,
                f"Rejected mechanic application for '{mechanic.user.username}'. Reason: {reason or 'No reason specified'}.",
                target=mechanic
            )
            messages.warning(request, f"Mechanic application for '{mechanic.user.username}' has been marked as REJECTED.")

        return redirect('admin_dashboard:mechanic_detail', pk=pk)

    # Active requests assigned to this mechanic
    assigned_requests = mechanic.assigned_service_requests.select_related('customer', 'vehicle').order_by('-created_at')[:8]

    return render(request, 'admin_dashboard/mechanic_detail.html', {
        'page_title': f"Audit Mechanic: {mechanic.user.username} | AutoVia Admin",
        'mechanic': mechanic,
        'assigned_requests': assigned_requests,
    })


# -------------------------------------------------------------
# 4. Workshop Verification & Management
# -------------------------------------------------------------

@admin_required
def admin_workshop_list(request):
    """Browse, filter, and audit all workshop service centres."""
    status_filter = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()

    workshops = Workshop.objects.select_related('owner').order_by('-created_at')

    if status_filter:
        workshops = workshops.filter(verification_status=status_filter)

    if query:
        workshops = workshops.filter(
            Q(workshop_name__icontains=query) |
            Q(owner__username__icontains=query) |
            Q(owner__email__icontains=query) |
            Q(address__icontains=query) |
            Q(services_offered__icontains=query)
        )

    context = {
        'page_title': 'Workshop Verification Management | AutoVia Admin',
        'workshops': workshops,
        'status_filter': status_filter,
        'query': query,
        'statuses': Workshop.VerificationStatus.choices,
        'pending_count': Workshop.objects.filter(verification_status=Workshop.VerificationStatus.PENDING).count(),
    }
    return render(request, 'admin_dashboard/workshops.html', context)


@admin_required
def admin_workshop_detail_verify(request, pk):
    """Inspect workshop facility details, approve, reject, or suspend."""
    workshop = get_object_or_404(Workshop.objects.select_related('owner'), pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('rejection_reason', '').strip()

        if action == 'approve':
            workshop.verification_status = Workshop.VerificationStatus.APPROVED
            workshop.rejection_reason = ''
            workshop.save()

            log_activity(
                request.user,
                ActivityLog.ActionType.WORKSHOP_VERIFICATION,
                f"Accredited workshop facility '{workshop.workshop_name}' (Owner: {workshop.owner.username}).",
                target=workshop
            )
            messages.success(request, f"Workshop '{workshop.workshop_name}' has been APPROVED.")

        elif action == 'reject':
            workshop.verification_status = Workshop.VerificationStatus.REJECTED
            workshop.rejection_reason = reason
            workshop.save()

            log_activity(
                request.user,
                ActivityLog.ActionType.WORKSHOP_VERIFICATION,
                f"Rejected workshop application for '{workshop.workshop_name}'. Reason: {reason or 'No reason specified'}.",
                target=workshop
            )
            messages.warning(request, f"Workshop application for '{workshop.workshop_name}' has been REJECTED.")

        elif action == 'suspend':
            workshop.verification_status = Workshop.VerificationStatus.SUSPENDED
            workshop.rejection_reason = reason
            workshop.save()

            # Optional owner deactivation
            if (request.POST.get('deactivate_owner') == '1' or request.POST.get('deactivate_user') == '1') and workshop.owner.pk != request.user.pk:
                workshop.owner.is_active = False
                workshop.owner.save()

            log_activity(
                request.user,
                ActivityLog.ActionType.WORKSHOP_VERIFICATION,
                f"Suspended workshop '{workshop.workshop_name}'. Reason: {reason or 'Operational suspension'}.",
                target=workshop
            )
            messages.error(request, f"Workshop '{workshop.workshop_name}' has been SUSPENDED.")

        return redirect('admin_dashboard:workshop_detail', pk=pk)

    assigned_requests = workshop.assigned_service_requests.select_related('customer', 'vehicle').order_by('-created_at')[:8]
    feedbacks = workshop.feedbacks.select_related('customer').order_by('-created_at')[:5]

    return render(request, 'admin_dashboard/workshop_detail.html', {
        'page_title': f"Audit Workshop: {workshop.workshop_name} | AutoVia Admin",
        'workshop': workshop,
        'assigned_requests': assigned_requests,
        'feedbacks': feedbacks,
    })


# -------------------------------------------------------------
# 5. Supplier Verification & Management
# -------------------------------------------------------------

@admin_required
def admin_supplier_list(request):
    """Browse, filter, and audit spare parts supplier enterprises."""
    status_filter = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()

    suppliers = SupplierProfile.objects.select_related('user', 'user__profile').order_by('-created_at')

    if status_filter:
        suppliers = suppliers.filter(verification_status=status_filter)

    if query:
        suppliers = suppliers.filter(
            Q(business_name__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query) |
            Q(business_address__icontains=query) |
            Q(phone_number__icontains=query)
        )

    context = {
        'page_title': 'Supplier Verification Management | AutoVia Admin',
        'suppliers': suppliers,
        'status_filter': status_filter,
        'query': query,
        'statuses': SupplierProfile.VerificationStatus.choices,
        'pending_count': SupplierProfile.objects.filter(verification_status=SupplierProfile.VerificationStatus.PENDING).count(),
    }
    return render(request, 'admin_dashboard/suppliers.html', context)


@admin_required
def admin_supplier_detail_verify(request, pk):
    """Inspect supplier warehouse profile, catalog volume, approve, reject, or suspend."""
    supplier = get_object_or_404(SupplierProfile.objects.select_related('user', 'user__profile'), pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('rejection_reason', '').strip()

        if action == 'approve':
            supplier.verification_status = SupplierProfile.VerificationStatus.APPROVED
            supplier.rejection_reason = ''
            supplier.save()

            log_activity(
                request.user,
                ActivityLog.ActionType.SUPPLIER_VERIFICATION,
                f"Approved spare parts supplier enterprise '{supplier.business_name}' (User: {supplier.user.username}).",
                target=supplier
            )
            messages.success(request, f"Supplier '{supplier.business_name}' has been APPROVED.")

        elif action == 'reject':
            supplier.verification_status = SupplierProfile.VerificationStatus.REJECTED
            supplier.rejection_reason = reason
            supplier.save()

            log_activity(
                request.user,
                ActivityLog.ActionType.SUPPLIER_VERIFICATION,
                f"Rejected supplier registration for '{supplier.business_name}'. Reason: {reason or 'No reason specified'}.",
                target=supplier
            )
            messages.warning(request, f"Supplier application for '{supplier.business_name}' has been REJECTED.")

        elif action == 'suspend':
            supplier.verification_status = SupplierProfile.VerificationStatus.SUSPENDED
            supplier.rejection_reason = reason
            supplier.save()

            if request.POST.get('deactivate_user') == '1' and supplier.user.pk != request.user.pk:
                supplier.user.is_active = False
                supplier.user.save()

            log_activity(
                request.user,
                ActivityLog.ActionType.SUPPLIER_VERIFICATION,
                f"Suspended supplier enterprise '{supplier.business_name}'. Reason: {reason or 'Trade compliance suspension'}.",
                target=supplier
            )
            messages.error(request, f"Supplier enterprise '{supplier.business_name}' has been SUSPENDED.")

        return redirect('admin_dashboard:supplier_detail', pk=pk)

    parts_sample = supplier.spare_parts.order_by('-created_at')[:8]
    total_parts = supplier.spare_parts.count()

    return render(request, 'admin_dashboard/supplier_detail.html', {
        'page_title': f"Audit Supplier: {supplier.business_name} | AutoVia Admin",
        'supplier': supplier,
        'parts_sample': parts_sample,
        'total_parts': total_parts,
    })


# -------------------------------------------------------------
# 6. Service Request Monitoring
# -------------------------------------------------------------

@admin_required
def admin_service_list(request):
    """
    Central operational monitor for all service tickets across the platform.
    Allows searching, filtering, and identifying overdue requests without mutating data.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    provider_type = request.GET.get('provider', '').strip()
    overdue_only = request.GET.get('overdue') == '1'

    services_qs = ServiceRequest.objects.select_related(
        'customer', 'vehicle', 'mechanic', 'workshop'
    ).order_by('-created_at')

    if query:
        # Check if query is an integer for ID lookup
        id_query = None
        if query.isdigit():
            id_query = int(query)
        elif query.startswith('#') and query[1:].isdigit():
            id_query = int(query[1:])

        if id_query:
            services_qs = services_qs.filter(pk=id_query)
        else:
            services_qs = services_qs.filter(
                Q(customer__username__icontains=query) |
                Q(customer__first_name__icontains=query) |
                Q(customer__last_name__icontains=query) |
                Q(vehicle__registration_number__icontains=query) |
                Q(vehicle__model_name__icontains=query) |
                Q(problem_description__icontains=query)
            )

    if status_filter:
        services_qs = services_qs.filter(status=status_filter)

    if provider_type == 'mechanic':
        services_qs = services_qs.filter(mechanic__isnull=False)
    elif provider_type == 'workshop':
        services_qs = services_qs.filter(workshop__isnull=False)
    elif provider_type == 'unassigned':
        services_qs = services_qs.filter(mechanic__isnull=True, workshop__isnull=True)

    if overdue_only:
        services_qs = services_qs.filter(
            requested_date__lt=timezone.now(),
            status__in=[
                ServiceRequest.Status.PENDING,
                ServiceRequest.Status.ACCEPTED,
                ServiceRequest.Status.IN_PROGRESS
            ]
        )

    paginator = Paginator(services_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_title': 'Service Requests Monitoring | AutoVia Admin',
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'provider_type': provider_type,
        'overdue_only': overdue_only,
        'statuses': ServiceRequest.Status.choices,
        'total_services': services_qs.count(),
        'now': timezone.now(),
    }
    return render(request, 'admin_dashboard/services.html', context)


@admin_required
def admin_service_detail(request, pk):
    """Detailed read-only inspection of an individual service request."""
    service = get_object_or_404(
        ServiceRequest.objects.select_related(
            'customer', 'vehicle', 'mechanic', 'workshop'
        ),
        pk=pk
    )

    estimates = service.estimates.select_related('provider').order_by('-created_at')
    bill = getattr(service, 'bill', None)
    feedback = getattr(service, 'feedback', None)
    complaints = service.complaints.select_related('user').order_by('-created_at')

    is_overdue = (
        service.requested_date < timezone.now() and
        service.status in [
            ServiceRequest.Status.PENDING,
            ServiceRequest.Status.ACCEPTED,
            ServiceRequest.Status.IN_PROGRESS
        ]
    )

    return render(request, 'admin_dashboard/service_detail.html', {
        'page_title': f"Monitor Service #{service.pk} | AutoVia Admin",
        'service': service,
        'estimates': estimates,
        'bill': bill,
        'feedback': feedback,
        'complaints': complaints,
        'is_overdue': is_overdue,
    })


# -------------------------------------------------------------
# 7. Complaint Management
# -------------------------------------------------------------

@admin_required
def admin_complaint_list(request):
    """View customer complaints, filter by status, and search."""
    status_filter = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()

    complaints = Complaint.objects.select_related('user', 'service_request', 'resolved_by').order_by('-created_at')

    if status_filter:
        complaints = complaints.filter(status=status_filter)

    if query:
        complaints = complaints.filter(
            Q(subject__icontains=query) |
            Q(description__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query)
        )

    context = {
        'page_title': 'Complaint Resolution & Dispute Management | AutoVia Admin',
        'complaints': complaints,
        'status_filter': status_filter,
        'query': query,
        'statuses': Complaint.Status.choices,
        'open_count': Complaint.objects.filter(status=Complaint.Status.OPEN).count(),
        'unresolved_count': Complaint.objects.filter(status__in=[Complaint.Status.OPEN, Complaint.Status.IN_PROGRESS]).count(),
    }
    return render(request, 'admin_dashboard/complaints.html', context)


@admin_required
def admin_complaint_detail_respond(request, pk):
    """Inspect complaint details, assign administrative response, resolve or reject."""
    complaint = get_object_or_404(
        Complaint.objects.select_related('user', 'service_request', 'resolved_by'),
        pk=pk
    )

    if request.method == 'POST':
        new_status = request.POST.get('status')
        admin_response = request.POST.get('admin_response', '').strip()

        valid_statuses = [c[0] for c in Complaint.Status.choices]
        if new_status in valid_statuses:
            complaint.status = new_status
            complaint.admin_response = admin_response

            if new_status in [Complaint.Status.RESOLVED, Complaint.Status.REJECTED, Complaint.Status.CLOSED]:
                complaint.resolved_by = request.user
                complaint.resolved_at = timezone.now()

            complaint.save()

            log_activity(
                request.user,
                ActivityLog.ActionType.COMPLAINT_UPDATE,
                f"Updated complaint #{complaint.pk} to '{complaint.get_status_display()}' with administrative resolution note.",
                target=complaint
            )
            messages.success(request, f"Complaint #{complaint.pk} status updated to: {complaint.get_status_display()}.")
        else:
            messages.error(request, "Invalid complaint status specified.")

        return redirect('admin_dashboard:complaint_detail', pk=pk)

    return render(request, 'admin_dashboard/complaint_detail.html', {
        'page_title': f"Complaint #{complaint.pk}: {complaint.subject} | AutoVia Admin",
        'complaint': complaint,
        'statuses': Complaint.Status.choices,
    })


# -------------------------------------------------------------
# 8. Platform Activity Monitoring
# -------------------------------------------------------------

@admin_required
def admin_activity_list(request):
    """Audit log console displaying platform events, administrative changes, and actor details."""
    action_type = request.GET.get('type', '').strip()
    query = request.GET.get('q', '').strip()

    activities_qs = ActivityLog.objects.select_related('user').order_by('-created_at')

    if action_type:
        activities_qs = activities_qs.filter(action_type=action_type)

    if query:
        activities_qs = activities_qs.filter(
            Q(description__icontains=query) |
            Q(user__username__icontains=query) |
            Q(target_repr__icontains=query)
        )

    paginator = Paginator(activities_qs, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_title': 'Platform Audit & Activity Log | AutoVia Admin',
        'page_obj': page_obj,
        'action_type': action_type,
        'query': query,
        'action_types': ActivityLog.ActionType.choices,
        'total_logs': activities_qs.count(),
    }
    return render(request, 'admin_dashboard/activities.html', context)
