from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehicle', 'owner', 'category', 'amount', 'expense_date', 'created_at')
    list_filter = ('category', 'expense_date', 'created_at')
    search_fields = ('vehicle__registration_number', 'owner__username', 'description')
