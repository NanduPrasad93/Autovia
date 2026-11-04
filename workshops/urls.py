from django.urls import path
from . import views

app_name = 'workshops'

urlpatterns = [
    path('', views.workshop_dashboard, name='dashboard'),
    path('dashboard/', views.workshop_dashboard, name='dashboard_alias'),
    path('profile/', views.workshop_profile, name='profile'),
    path('verification/', views.verification_status_view, name='verification_status'),
    path('requests/', views.incoming_requests, name='incoming_requests'),
    path('requests/<int:pk>/', views.workshop_request_detail, name='request_detail'),
    path('requests/<int:pk>/accept/', views.accept_request, name='accept_request'),
    path('requests/<int:pk>/reject/', views.reject_request, name='reject_request'),
    path('requests/<int:pk>/estimate/', views.create_or_edit_estimate, name='create_estimate'),
    path('estimates/', views.estimate_list, name='estimates'),
    path('estimates/<int:pk>/edit/', views.create_or_edit_estimate, name='edit_estimate'),
    path('repairs/', views.active_repairs, name='active_repairs'),
    path('repairs/<int:pk>/status/', views.update_repair_status, name='update_repair_status'),
    path('repairs/<int:pk>/bill/', views.generate_bill, name='generate_bill'),
    path('bills/<int:pk>/', views.bill_detail, name='bill_detail'),
    path('history/', views.service_history, name='service_history'),
    path('feedback/', views.customer_feedback, name='feedback'),
    path('analytics/', views.business_analytics, name='analytics'),
]
