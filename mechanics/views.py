from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from accounts.decorators import vehicle_owner_required
from .models import MechanicProfile


@vehicle_owner_required
def mechanic_list(request):
    """
    Display approved / verified professional mechanics available for service requests.
    Supports search filtering by name, specialization, or service location.
    """
    query = request.GET.get('q', '').strip()
    specialization = request.GET.get('specialization', '').strip()

    mechanics = MechanicProfile.objects.all()

    # Filter by verified status for approved providers
    # If the user explicitly checks show_all (or in development), we allow filtering
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
    """View detailed mechanic profile and initiate service requests."""
    mechanic = get_object_or_404(MechanicProfile, pk=pk)
    user_vehicles = request.user.vehicles.all()

    return render(request, 'mechanics/mechanic_detail.html', {
        'mechanic': mechanic,
        'user_vehicles': user_vehicles,
        'page_title': f"Mechanic: {mechanic.user.get_full_name() or mechanic.user.username} | AutoVia",
    })
