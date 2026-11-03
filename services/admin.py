from django.contrib import admin
from .models import ServiceRequest, RepairEstimate, ServiceRecord


class RepairEstimateInline(admin.StackedInline):
    model = RepairEstimate
    extra = 0


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehicle', 'customer', 'mechanic', 'workshop', 'status', 'requested_date', 'created_at')
    list_filter = ('status', 'requested_date', 'created_at')
    search_fields = ('id', 'vehicle__registration_number', 'customer__username', 'problem_description')
    inlines = [RepairEstimateInline]


@admin.register(RepairEstimate)
class RepairEstimateAdmin(admin.ModelAdmin):
    list_display = ('id', 'service_request', 'provider', 'labor_cost', 'parts_cost', 'additional_cost', 'total_cost', 'estimated_completion_date')
    list_filter = ('estimated_completion_date', 'created_at')
    search_fields = ('id', 'service_request__id', 'provider__username', 'description')


@admin.register(ServiceRecord)
class ServiceRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehicle', 'service_date', 'odometer_reading', 'total_cost', 'created_at')
    list_filter = ('service_date', 'created_at')
    search_fields = ('vehicle__registration_number', 'service_description')
