from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication & Registration
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Role Dashboards
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    path('dashboard/vehicle-owner/', views.vehicle_owner_dashboard, name='vehicle_owner_dashboard'),
    path('dashboard/mechanic/', views.mechanic_dashboard, name='mechanic_dashboard'),
    path('dashboard/workshop/', views.workshop_dashboard, name='workshop_dashboard'),
    path('dashboard/supplier/', views.supplier_dashboard, name='supplier_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),

    # Profile Management
    path('profile/', views.profile_view, name='profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),

    # Password Reset Workflow
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
