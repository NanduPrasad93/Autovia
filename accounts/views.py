from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.urls import reverse_lazy

from .models import UserProfile
from .forms import LoginForm, RegistrationForm
from .decorators import (
    role_required,
    vehicle_owner_required,
    mechanic_required,
    workshop_required,
    supplier_required,
    admin_required,
)
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
    return render(request, 'accounts/dashboards/vehicle_owner.html', {
        'role_title': 'Vehicle Owner',
        'page_title': 'Vehicle Owner Dashboard | AutoVia',
    })


@mechanic_required
def mechanic_dashboard(request):
    return render(request, 'accounts/dashboards/mechanic.html', {
        'role_title': 'Professional Mechanic',
        'page_title': 'Mechanic Dashboard | AutoVia',
    })


@workshop_required
def workshop_dashboard(request):
    return render(request, 'accounts/dashboards/workshop.html', {
        'role_title': 'Workshop & Service Centre',
        'page_title': 'Workshop Dashboard | AutoVia',
    })


@supplier_required
def supplier_dashboard(request):
    return render(request, 'accounts/dashboards/supplier.html', {
        'role_title': 'Spare Parts Supplier',
        'page_title': 'Supplier Dashboard | AutoVia',
    })


@admin_required
def admin_dashboard(request):
    return render(request, 'accounts/dashboards/admin_dashboard.html', {
        'role_title': 'Platform Administrator',
        'page_title': 'Admin Dashboard | AutoVia',
    })


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
