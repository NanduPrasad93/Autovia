from django.urls import path
from . import views

app_name = 'mechanics'

urlpatterns = [
    # Dashboard & Profile
    path('dashboard/', views.mechanic_dashboard, name='dashboard'),
    path('profile/', views.mechanic_profile_edit, name='profile'),
    path('availability/', views.availability_view, name='availability'),
    path('availability/toggle/', views.toggle_availability, name='toggle_availability'),

    # Service Request Management
    path('requests/', views.incoming_requests, name='incoming_requests'),
    path('requests/<int:pk>/', views.mechanic_request_detail, name='request_detail'),
    path('requests/<int:pk>/accept/', views.accept_request, name='accept_request'),
    path('requests/<int:pk>/reject/', views.reject_request, name='reject_request'),

    # Estimates
    path('requests/<int:pk>/estimate/', views.create_or_edit_estimate, name='create_estimate'),
    path('estimates/', views.estimate_list, name='estimate_list'),

    # Active Repairs
    path('active-repairs/', views.active_repairs, name='active_repairs'),
    path('repairs/<int:pk>/update-status/', views.update_repair_status, name='update_repair_status'),
    path('repairs/<int:pk>/generate-bill/', views.generate_bill, name='generate_bill'),

    # Bills & Invoices
    path('bills/', views.bill_list, name='bill_list'),
    path('bills/<int:pk>/', views.bill_detail, name='bill_detail'),

    # Customer Reviews & Feedback
    path('feedback/', views.feedback_list, name='feedback_list'),

    # Customer Facing Directory (Preserved)
    path('find/', views.mechanic_list, name='find_mechanics'),
    path('<int:pk>/', views.mechanic_detail, name='mechanic_detail'),
]
