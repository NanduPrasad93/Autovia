from django.contrib import admin
from .models import Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'manufacturer', 'model_name', 'owner', 'fuel_type', 'manufacturing_year', 'current_odometer')
    list_filter = ('fuel_type', 'manufacturing_year', 'created_at')
    search_fields = ('registration_number', 'manufacturer', 'model_name', 'chassis_number', 'owner__username')
