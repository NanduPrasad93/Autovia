from django.urls import path
from . import views

app_name = 'suppliers'

urlpatterns = [
    path('', views.supplier_dashboard, name='dashboard'),
    path('dashboard/', views.supplier_dashboard, name='dashboard_alias'),
    path('profile/', views.supplier_profile, name='profile'),
    path('verification/', views.verification_status_view, name='verification'),
    path('products/', views.product_list, name='products'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('inventory/', views.inventory_management, name='inventory'),
    path('orders/', views.order_list, name='orders'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/status/', views.update_order_status, name='update_order_status'),
    path('sales/', views.sales_reports, name='sales'),
]
