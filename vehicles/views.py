from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from accounts.decorators import vehicle_owner_required
from .models import Vehicle
from .forms import VehicleForm
from services.models import ServiceRequest, ServiceRecord
from expenses.models import Expense


@vehicle_owner_required
def vehicle_list(request):
    """Display all vehicles belonging to the logged-in vehicle owner."""
    vehicles = Vehicle.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'vehicles/vehicle_list.html', {
        'vehicles': vehicles,
        'page_title': 'My Vehicles | AutoVia',
    })


@vehicle_owner_required
def vehicle_add(request):
    """Add a new vehicle to the owner's fleet."""
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.owner = request.user
            vehicle.save()
            messages.success(request, f"Vehicle '{vehicle.manufacturer} {vehicle.model_name}' ({vehicle.registration_number}) successfully registered!")
            return redirect('vehicles:list')
    else:
        form = VehicleForm()

    return render(request, 'vehicles/vehicle_form.html', {
        'form': form,
        'is_edit': False,
        'page_title': 'Add New Vehicle | AutoVia',
    })


@vehicle_owner_required
def vehicle_detail(request, pk):
    """Display comprehensive vehicle details, maintenance history, requests, and expenses."""
    vehicle = get_object_or_404(Vehicle, pk=pk, owner=request.user)
    service_requests = ServiceRequest.objects.filter(vehicle=vehicle).order_by('-created_at')
    service_records = ServiceRecord.objects.filter(vehicle=vehicle).order_by('-service_date')
    expenses = Expense.objects.filter(vehicle=vehicle).order_by('-expense_date')

    total_expenses = sum((e.amount for e in expenses), 0)

    return render(request, 'vehicles/vehicle_detail.html', {
        'vehicle': vehicle,
        'service_requests': service_requests,
        'service_records': service_records,
        'expenses': expenses,
        'total_expenses': total_expenses,
        'page_title': f"{vehicle.manufacturer} {vehicle.model_name} | AutoVia",
    })


@vehicle_owner_required
def vehicle_edit(request, pk):
    """Edit existing vehicle parameters."""
    vehicle = get_object_or_404(Vehicle, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, f"Vehicle '{vehicle.registration_number}' successfully updated.")
            return redirect('vehicles:detail', pk=vehicle.pk)
    else:
        form = VehicleForm(instance=vehicle)

    return render(request, 'vehicles/vehicle_form.html', {
        'form': form,
        'vehicle': vehicle,
        'is_edit': True,
        'page_title': f"Edit {vehicle.registration_number} | AutoVia",
    })


@vehicle_owner_required
@require_POST
def vehicle_delete(request, pk):
    """Delete a vehicle owned by the user."""
    vehicle = get_object_or_404(Vehicle, pk=pk, owner=request.user)
    reg_num = vehicle.registration_number
    vehicle.delete()
    messages.success(request, f"Vehicle '{reg_num}' has been removed from your garage.")
    return redirect('vehicles:list')
