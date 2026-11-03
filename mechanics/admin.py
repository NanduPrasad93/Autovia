from django.contrib import admin
from .models import MechanicProfile


@admin.register(MechanicProfile)
class MechanicProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'experience_years', 'service_location', 'is_available', 'verification_status', 'created_at')
    list_filter = ('is_available', 'verification_status', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'specialization', 'service_location')
