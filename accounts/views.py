from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.urls import reverse, reverse_lazy
from decimal import Decimal
import json
import datetime

from .models import UserProfile
from .forms import LoginForm, RegistrationForm, ProfileUpdateForm
from .decorators import (
    role_required,
    vehicle_owner_required,
    mechanic_required,
    workshop_required,
    supplier_required,
    admin_required,
)
from vehicles.models import Vehicle
from services.models import ServiceRequest, ServiceRecord
from expenses.models import Expense
from mechanics.models import MechanicProfile
from workshops.models import Workshop
from suppliers.models import SupplierProfile


def get_role_dashboard_url(user):
    """Determine the destination dashboard for a given authenticated user."""
    if user.is_superuser or user.is_staff:
        return 'accounts:admin_dashboard'

    profile = getattr(user, 'profile', None)
    if profile:
        mapping = {
            UserProfile.Role.VEHICLE_OWNER: 'accounts:vehicle_owner_dashboard',
            UserProfile.Role.MECHANIC: 'accounts:mechanic_dashboard',
            UserProfile.Role.WORKSHOP: 'accounts:workshop_dashboard',
            UserProfile.Role.SUPPLIER: 'accounts:supplier_dashboard',
            UserProfile.Role.ADMIN: 'accounts:admin_dashboard',
        }
        return mapping.get(profile.role, 'core:home')
    return 'core:home'


def login_view(request):
    """Handle user login with username or email authentication."""
    if request.user.is_authenticated:
        return redirect(get_role_dashboard_url(request.user))

    redirect_to = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me')

            user = authenticate(request, username=username_or_email, password=password)
            if user is not None:
                if not user.is_active:
                    messages.error(request, "This account is inactive. Please contact support.")
                    return render(request, 'accounts/login.html', {'form': form, 'next': redirect_to})

                login(request, user)

                # Remember-me handling: 30 days if checked, session expiration on browser close if unchecked
                if remember_me:
                    request.session.set_expiry(2592000)  # 30 days
                else:
                    request.session.set_expiry(0)  # On browser close

                messages.success(request, f"Welcome back, {user.first_name or user.username}!")

                # Safe redirect handling to prevent open redirects
                if redirect_to and url_has_allowed_host_and_scheme(redirect_to, allowed_hosts={request.get_host()}):
                    return redirect(redirect_to)

                return redirect(get_role_dashboard_url(user))
            else:
                messages.error(request, "Invalid username/email or password. Please try again.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {
        'form': form,
        'next': redirect_to,
        'page_title': 'Login | AutoVia',
    })


def register_view(request):
    """Handle user registration with atomic creation of profiles."""
    if request.user.is_authenticated:
        return redirect(get_role_dashboard_url(request.user))

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data.get('full_name').strip()
            username = form.cleaned_data.get('username').strip()
            email = form.cleaned_data.get('email').strip().lower()
            phone_number = form.cleaned_data.get('phone_number').strip()
            account_type = form.cleaned_data.get('account_type')
            password = form.cleaned_data.get('password')

            # Parse first and last names
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            try:
                with transaction.atomic():
                    # 1. Create Django User
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name
                    )

                    # 2. Update UserProfile created by signal
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.role = account_type
                    profile.phone_number = phone_number
                    profile.save()

                    # 3. Create associated specialized provider profiles with PENDING status
                    if account_type == UserProfile.Role.MECHANIC:
                        MechanicProfile.objects.create(
                            user=user,
                            specialization='General Automobile Maintenance',
                            experience_years=0,
                            service_location='City Wide',
                            description='Pending profile completion.',
                            is_available=True,
                            verification_status=MechanicProfile.VerificationStatus.PENDING
                        )
                    elif account_type == UserProfile.Role.WORKSHOP:
                        Workshop.objects.create(
                            owner=user,
                            workshop_name=f"{full_name}'s Workshop",
                            description='Pending workshop details.',
                            address='Address pending verification',
                            phone_number=phone_number,
                            services_offered='General Vehicle Servicing & Repairs',
                            verification_status=Workshop.VerificationStatus.PENDING
                        )
                    elif account_type == UserProfile.Role.SUPPLIER:
                        SupplierProfile.objects.create(
                            user=user,
                            business_name=f"{full_name}'s Auto Supplies",
                            business_address='Address pending verification',
                            phone_number=phone_number,
                            verification_status=SupplierProfile.VerificationStatus.PENDING
                        )

                messages.success(request, "Registration successful! Your account has been created. Please log in.")
                return redirect('accounts:login')

            except Exception as e:
                messages.error(request, f"An error occurred while creating your account: {str(e)}")
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {
        'form': form,
        'page_title': 'Register | AutoVia',
    })


@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    Safely logout the authenticated user and invalidate session.
    Accepts POST requests (standard) and GET for user convenience.
    """
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "You have been logged out securely.")
    return redirect('core:home')


def dashboard_redirect(request):
    """Redirect logged in user to their specific dashboard based on role."""
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    return redirect(get_role_dashboard_url(request.user))


# Role-protected dashboard placeholder views

@vehicle_owner_required
def vehicle_owner_dashboard(request):
    user = request.user
    vehicles = user.vehicles.all()
    total_vehicles = vehicles.count()

    pending_requests_count = ServiceRequest.objects.filter(
        customer=user,
        status=ServiceRequest.Status.PENDING
    ).count()

    completed_services_count = ServiceRecord.objects.filter(
        vehicle__owner=user
    ).count()

    total_expenses = Expense.objects.filter(
        owner=user
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    recent_requests = ServiceRequest.objects.filter(
        customer=user
    ).select_related('vehicle', 'mechanic__user', 'workshop').order_by('-created_at')[:5]

    recent_expenses = Expense.objects.filter(
        owner=user
    ).select_related('vehicle').order_by('-expense_date', '-created_at')[:5]

    # Dynamic maintenance reminders based on mileage and history
    maintenance_reminders = []
    for v in vehicles:
        if v.current_odometer >= 10000:
            maintenance_reminders.append({
                'vehicle': v,
                'level': 'warning',
                'title': f'{v.manufacturer} {v.model_name} (Over 10,000 km)',
                'message': f'Current odometer is {v.current_odometer:,} km. Brake system diagnostics, wheel alignment, and fluid checks are recommended.',
                'action_url': f"{reverse('services:request_create')}?vehicle_id={v.id}",
            })
        elif v.current_odometer >= 5000:
            maintenance_reminders.append({
                'vehicle': v,
                'level': 'info',
                'title': f'{v.manufacturer} {v.model_name} (Routine Service)',
                'message': f'Current odometer is {v.current_odometer:,} km. Engine oil and filter change is recommended every 5,000–7,500 km.',
                'action_url': f"{reverse('services:request_create')}?vehicle_id={v.id}",
            })

        has_records = ServiceRecord.objects.filter(vehicle=v).exists()
        if not has_records and v.current_odometer < 5000:
            maintenance_reminders.append({
                'vehicle': v,
                'level': 'secondary',
                'title': f'{v.manufacturer} {v.model_name} (New Vehicle Check)',
                'message': 'No past maintenance log on record. Schedule a baseline inspection or tune-up.',
                'action_url': f"{reverse('services:request_create')}?vehicle_id={v.id}",
            })

    # Chart.js visualizations
    # 1. Category breakdown
    cat_aggregates = Expense.objects.filter(owner=user).values('category').annotate(total=Sum('amount')).order_by('-total')
    cat_map = dict(Expense.Category.choices)
    category_labels = [cat_map.get(item['category'], item['category']) for item in cat_aggregates]
    category_data = [float(item['total']) for item in cat_aggregates]

    # 2. Monthly Trend (last 6 months)
    today = datetime.date.today()
    monthly_labels = []
    monthly_data = []
    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_label = datetime.date(year, month, 1).strftime('%b %Y')
        month_sum = Expense.objects.filter(
            owner=user,
            expense_date__year=year,
            expense_date__month=month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        monthly_labels.append(month_label)
        monthly_data.append(float(month_sum))

    context = {
        'role_title': 'Vehicle Owner',
        'page_title': 'Vehicle Owner Dashboard | AutoVia',
        'total_vehicles': total_vehicles,
        'pending_requests_count': pending_requests_count,
        'completed_services_count': completed_services_count,
        'total_expenses': total_expenses,
        'recent_requests': recent_requests,
        'recent_expenses': recent_expenses,
        'vehicles': vehicles[:6],
        'maintenance_reminders': maintenance_reminders,
        'category_labels_json': json.dumps(category_labels),
        'category_data_json': json.dumps(category_data),
        'monthly_labels_json': json.dumps(monthly_labels),
        'monthly_data_json': json.dumps(monthly_data),
    }
    return render(request, 'accounts/dashboards/vehicle_owner.html', context)


@login_required
def profile_view(request):
    """View and update user profile information."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()
            profile.phone_number = form.cleaned_data['phone_number']
            profile.address = form.cleaned_data['address']
            profile.save()
            messages.success(request, "Your profile details have been updated successfully.")
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'phone_number': profile.phone_number or '',
            'address': profile.address or '',
        })

    pending_requests_count = 0
    if hasattr(request.user, 'profile') and request.user.profile.role == UserProfile.Role.VEHICLE_OWNER:
        pending_requests_count = ServiceRequest.objects.filter(
            customer=request.user,
            status=ServiceRequest.Status.PENDING
        ).count()

    return render(request, 'accounts/profile.html', {
        'form': form,
        'profile': profile,
        'pending_requests_count': pending_requests_count,
        'page_title': 'Profile Settings | AutoVia',
    })


@login_required
def change_password_view(request):
    """Allow authenticated users to securely update their password."""
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was changed successfully.")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please correct the errors indicated below.")
    else:
        form = PasswordChangeForm(user=request.user)

    pending_requests_count = 0
    if hasattr(request.user, 'profile') and request.user.profile.role == UserProfile.Role.VEHICLE_OWNER:
        pending_requests_count = ServiceRequest.objects.filter(
            customer=request.user,
            status=ServiceRequest.Status.PENDING
        ).count()

    return render(request, 'accounts/change_password.html', {
        'form': form,
        'pending_requests_count': pending_requests_count,
        'page_title': 'Change Password | AutoVia',
    })


@mechanic_required
def mechanic_dashboard(request):
    from mechanics import views as mechanic_views
    return mechanic_views.mechanic_dashboard(request)


@workshop_required
def workshop_dashboard(request):
    from workshops import views as workshop_views
    return workshop_views.workshop_dashboard(request)


@supplier_required
def supplier_dashboard(request):
    from suppliers import views as supplier_views
    return supplier_views.supplier_dashboard(request)


@admin_required
def admin_dashboard(request):
    return redirect('admin_dashboard:dashboard')


# Password Reset Views

class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'
