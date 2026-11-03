from django.urls import path
from . import views

app_name = 'mechanics'

urlpatterns = [
    path('find/', views.mechanic_list, name='find_mechanics'),
    path('<int:pk>/', views.mechanic_detail, name='mechanic_detail'),
]
