from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('', views.expense_list, name='list'),
    path('add/', views.expense_add, name='add'),
    path('<int:pk>/edit/', views.expense_edit, name='edit'),
    path('<int:pk>/delete/', views.expense_delete, name='delete'),
    path('analytics/', views.expense_analytics, name='analytics'),
    path('export/', views.expense_export_csv, name='export_csv'),
]
