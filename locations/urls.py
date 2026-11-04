from django.urls import path
from . import views

app_name = 'locations'

urlpatterns = [
    path('stations/', views.nearby_stations, name='nearby_stations'),
    path('api/stations/', views.stations_api, name='stations_api'),
]
