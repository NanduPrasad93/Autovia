from django.urls import path
from . import admin_views as views

app_name = 'admin_dashboard'

urlpatterns = [
    # 1. Overview
    path('', views.admin_dashboard_overview, name='dashboard'),

    # 2. User Management
    path('users/', views.admin_user_list, name='users'),
    path('users/<int:pk>/', views.admin_user_detail, name='user_detail'),
    path('users/<int:pk>/toggle-status/', views.admin_user_toggle_status, name='user_toggle_status'),

    # 3. Mechanic Verification
    path('mechanics/', views.admin_mechanic_list, name='mechanics'),
    path('mechanics/<int:pk>/', views.admin_mechanic_detail_verify, name='mechanic_detail'),

    # 4. Workshop Verification & Accreditation
    path('workshops/', views.admin_workshop_list, name='workshops'),
    path('workshops/<int:pk>/', views.admin_workshop_detail_verify, name='workshop_detail'),

    # 5. Supplier Verification & Accreditation
    path('suppliers/', views.admin_supplier_list, name='suppliers'),
    path('suppliers/<int:pk>/', views.admin_supplier_detail_verify, name='supplier_detail'),

    # 6. Service Requests Monitoring
    path('services/', views.admin_service_list, name='services'),
    path('services/<int:pk>/', views.admin_service_detail, name='service_detail'),

    # 7. Customer Complaints & Resolution
    path('complaints/', views.admin_complaint_list, name='complaints'),
    path('complaints/<int:pk>/', views.admin_complaint_detail_respond, name='complaint_detail'),

    # 8. Platform Activity & Audit Logging
    path('activities/', views.admin_activity_list, name='activities'),
]
