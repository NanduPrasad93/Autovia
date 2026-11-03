from django.contrib import admin
from .models import SupplierProfile, SparePart, SparePartOrder, SparePartOrderItem


class SparePartOrderItemInline(admin.TabularInline):
    model = SparePartOrderItem
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(SupplierProfile)
class SupplierProfileAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'phone_number', 'verification_status', 'created_at')
    list_filter = ('verification_status', 'created_at')
    search_fields = ('business_name', 'user__username', 'phone_number', 'business_address')


@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = ('part_name', 'part_number', 'supplier', 'price', 'stock_quantity', 'updated_at')
    list_filter = ('supplier', 'created_at')
    search_fields = ('part_name', 'part_number', 'description', 'compatible_vehicle_models')


@admin.register(SparePartOrder)
class SparePartOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'status', 'total_amount', 'contact_phone', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'customer__username', 'contact_phone', 'shipping_address')
    inlines = [SparePartOrderItemInline]


@admin.register(SparePartOrderItem)
class SparePartOrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'part', 'quantity', 'unit_price', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('order__id', 'part__part_name', 'part__part_number')
