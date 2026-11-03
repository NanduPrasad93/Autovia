from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services_view, name='services'),
    path('contact/', views.contact, name='contact'),
    path('login/', views.login_placeholder, name='login'),
    path('register/', views.register_placeholder, name='register'),
]
