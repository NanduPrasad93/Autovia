from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from accounts.decorators import vehicle_owner_required
from .models import ServiceRequest, RepairEstimate, ServiceRecord
from .forms import ServiceRequestForm
from vehicles.models import Vehicle
from mechanics.models import MechanicProfile
from workshops.models import Workshop


@vehicle_owner_required
def service_request_list(request):
    """List all service requests created by the authenticated vehicle owner."""
    status_filter = request.GET.get('status', '').strip()
    requests = ServiceRequest.objects.filter(customer=request.user)

    if status_filter:
        requests = requests.filter(status=status_filter)

    requests = requests.order_by('-created_at')

    return render(request, 'services/service_request_list.html', {
        'service_requests': requests,
        'status_filter': status_filter,
        'page_title': 'Service Requests | AutoVia',
    })


@vehicle_owner_required
def service_request_create(request):
    """Submit a new service request for one of the owner's vehicles."""
    if not request.user.vehicles.exists():
        messages.warning(request, "Please register at least one vehicle before creating a service request.")
        return redirect('vehicles:add')

    initial_data = {
        'requested_date': timezone.now() + timezone.timedelta(days=1),
    }

    vehicle_id = request.GET.get('vehicle_id')
    if vehicle_id:
        vehicle = Vehicle.objects.filter(pk=vehicle_id, owner=request.user).first()
        if vehicle:
            initial_data['vehicle'] = vehicle

    mechanic_id = request.GET.get('mechanic_id')
    if mechanic_id:
        mechanic = MechanicProfile.objects.filter(pk=mechanic_id).first()
        if mechanic:
            initial_data['mechanic'] = mechanic

    workshop_id = request.GET.get('workshop_id')
    if workshop_id:
        workshop = Workshop.objects.filter(pk=workshop_id).first()
        if workshop:
            initial_data['workshop'] = workshop

    if request.method == 'POST':
        form = ServiceRequestForm(request.POST, user=request.user)
        if form.is_valid():
            req = form.save(commit=False)
            req.customer = request.user
            req.save()
            messages.success(request, f"Service Request #{req.id} for {req.vehicle.registration_number} created successfully!")
            return redirect('services:request_detail', pk=req.id)
    else:
        form = ServiceRequestForm(initial=initial_data, user=request.user)

    return render(request, 'services/service_request_form.html', {
        'form': form,
        'page_title': 'New Service Request | AutoVia',
    })


@vehicle_owner_required
def service_request_detail(request, pk):
    """View details of a service request and compare repair estimates."""
    service_request = get_object_or_404(ServiceRequest, pk=pk, customer=request.user)
    estimates = service_request.estimates.all().order_by('-created_at')

    return render(request, 'services/service_request_detail.html', {
        'service_request': service_request,
        'estimates': estimates,
        'page_title': f"Request #{service_request.id} Details | AutoVia",
    })


@vehicle_owner_required
@require_POST
def service_request_cancel(request, pk):
    """Cancel a pending service request."""
    service_request = get_object_or_404(ServiceRequest, pk=pk, customer=request.user)
    if service_request.status in [ServiceRequest.Status.PENDING, ServiceRequest.Status.ACCEPTED]:
        service_request.status = ServiceRequest.Status.CANCELLED
        service_request.save()
        messages.success(request, f"Service Request #{service_request.id} has been cancelled.")
    else:
        messages.error(request, f"Cannot cancel a request that is currently {service_request.get_status_display().lower()}.")
    return redirect('services:request_detail', pk=service_request.id)


@vehicle_owner_required
def service_history_list(request):
    """View historical completed service records for all vehicles owned by user."""
    records = ServiceRecord.objects.filter(vehicle__owner=request.user).order_by('-service_date', '-created_at')
    total_spent = sum((r.total_cost for r in records), 0)

    return render(request, 'services/service_history_list.html', {
        'records': records,
        'total_spent': total_spent,
        'page_title': 'Service History | AutoVia',
    })


@vehicle_owner_required
def service_record_detail(request, pk):
    """View individual service record details."""
    record = get_object_or_404(ServiceRecord, pk=pk, vehicle__owner=request.user)
    return render(request, 'services/service_record_detail.html', {
        'record': record,
        'page_title': f"Service Record #{record.id} | AutoVia",
    })
