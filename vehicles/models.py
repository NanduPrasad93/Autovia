from django.db import models
from django.contrib.auth.models import User
import datetime


def current_year():
    return datetime.date.today().year


class Vehicle(models.Model):
    class FuelType(models.TextChoices):
        PETROL = 'PETROL', 'Petrol'
        DIESEL = 'DIESEL', 'Diesel'
        CNG = 'CNG', 'CNG'
        HYBRID = 'HYBRID', 'Hybrid'
        ELECTRIC = 'ELECTRIC', 'Electric'

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicles')
    registration_number = models.CharField(max_length=50, unique=True, db_index=True)
    manufacturer = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    manufacturing_year = models.PositiveIntegerField(default=current_year)
    fuel_type = models.CharField(
        max_length=20,
        choices=FuelType.choices,
        default=FuelType.PETROL,
        db_index=True,
    )
    color = models.CharField(max_length=50)
    chassis_number = models.CharField(max_length=100, blank=True, null=True)
    current_odometer = models.PositiveIntegerField(default=0, help_text="Current odometer reading in kilometers/miles")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.manufacturer} {self.model_name} ({self.registration_number}) - {self.owner.username}"
