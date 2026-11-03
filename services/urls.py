from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    # Service Requests
    path('requests/', views.service_request_list, name='request_list'),
    path('requests/new/', views.service_request_create, name='request_create'),
    path('requests/<int:pk>/', views.service_request_detail, name='request_detail'),
    path('requests/<int:pk>/cancel/', views.service_request_cancel, name='request_cancel'),

    # Service History
    path('history/', views.service_history_list, name='history_list'),
    path('history/<int:pk>/', views.service_record_detail, name='record_detail'),
]
