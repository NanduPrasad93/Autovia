from django.db import models
from django.contrib.auth.models import User


class Expense(models.Model):
    class Category(models.TextChoices):
        FUEL = 'FUEL', 'Fuel'
        SERVICING = 'SERVICING', 'Servicing'
        REPAIR = 'REPAIR', 'Repair'
        SPARE_PARTS = 'SPARE_PARTS', 'Spare Parts'
        INSURANCE = 'INSURANCE', 'Insurance'
        EV_CHARGING = 'EV_CHARGING', 'EV Charging'
        OTHER = 'OTHER', 'Other'

    vehicle = models.ForeignKey('vehicles.Vehicle', on_delete=models.CASCADE, related_name='expenses')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
        db_index=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    expense_date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Expense'
        verbose_name_plural = 'Expenses'
        ordering = ['-expense_date', '-created_at']

    def __str__(self):
        return f"{self.get_category_display()} - ${self.amount} for {self.vehicle.registration_number} on {self.expense_date}"
