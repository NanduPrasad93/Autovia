from django.contrib import admin
from .models import Workshop


@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    list_display = ('workshop_name', 'owner', 'phone_number', 'verification_status', 'created_at')
    list_filter = ('verification_status', 'created_at')
    search_fields = ('workshop_name', 'owner__username', 'address', 'phone_number', 'services_offered')
