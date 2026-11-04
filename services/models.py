from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
import datetime


class ServiceRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    vehicle = models.ForeignKey('vehicles.Vehicle', on_delete=models.CASCADE, related_name='service_requests')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_service_requests')
    mechanic = models.ForeignKey(
        'mechanics.MechanicProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_service_requests',
    )
    workshop = models.ForeignKey(
        'workshops.Workshop',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_service_requests',
    )
    problem_description = models.TextField()
    requested_date = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Service Request'
        verbose_name_plural = 'Service Requests'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=~(models.Q(mechanic__isnull=False) & models.Q(workshop__isnull=False)),
                name='service_request_at_most_one_provider',
            )
        ]

    def clean(self):
        super().clean()
        if self.mechanic and self.workshop:
            raise ValidationError("A service request cannot have both an individual mechanic and a workshop assigned simultaneously.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        provider = self.mechanic or self.workshop or "Unassigned"
        return f"Request #{self.pk}: {self.vehicle.registration_number} - {self.get_status_display()} ({provider})"


class RepairEstimate(models.Model):
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='estimates')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='repair_estimates')
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    parts_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    additional_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    estimated_completion_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Repair Estimate'
        verbose_name_plural = 'Repair Estimates'
        ordering = ['-created_at']

    def calculate_total(self):
        return (self.labor_cost or Decimal('0.00')) + (self.parts_cost or Decimal('0.00')) + (self.additional_cost or Decimal('0.00'))

    def save(self, *args, **kwargs):
        self.total_cost = self.calculate_total()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Estimate #{self.pk} for Request #{self.service_request.pk} - ${self.total_cost}"


class ServiceRecord(models.Model):
    vehicle = models.ForeignKey('vehicles.Vehicle', on_delete=models.CASCADE, related_name='service_records')
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_records',
    )
    service_description = models.TextField()
    service_date = models.DateField()
    odometer_reading = models.PositiveIntegerField(help_text="Odometer reading at time of service")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Service Record'
        verbose_name_plural = 'Service Records'
        ordering = ['-service_date', '-created_at']

    def __str__(self):
        return f"Record for {self.vehicle.registration_number} on {self.service_date} - ${self.total_cost}"


class RepairBill(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', 'Cash'
        CARD = 'CARD', 'Credit / Debit Card'
        ONLINE = 'ONLINE', 'Online Transfer / UPI'

    service_request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name='bill')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='issued_repair_bills')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_repair_bills')
    vehicle = models.ForeignKey('vehicles.Vehicle', on_delete=models.CASCADE, related_name='repair_bills')
    service_description = models.TextField()
    labor_charges = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    parts_charges = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    additional_charges = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    service_date = models.DateField(default=datetime.date.today)
    is_paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Repair Bill'
        verbose_name_plural = 'Repair Bills'
        ordering = ['-service_date', '-created_at']

    def calculate_total(self):
        return (self.labor_charges or Decimal('0.00')) + (self.parts_charges or Decimal('0.00')) + (self.additional_charges or Decimal('0.00'))

    def save(self, *args, **kwargs):
        self.total_amount = self.calculate_total()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Bill #{self.pk} for Request #{self.service_request.pk} - ${self.total_amount}"


class ServiceFeedback(models.Model):
    service_request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name='feedback')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_feedbacks')
    mechanic = models.ForeignKey('mechanics.MechanicProfile', on_delete=models.CASCADE, null=True, blank=True, related_name='feedbacks')
    workshop = models.ForeignKey('workshops.Workshop', on_delete=models.CASCADE, null=True, blank=True, related_name='feedbacks')
    rating = models.PositiveSmallIntegerField(
        choices=[(1, '1 Star'), (2, '2 Stars'), (3, '3 Stars'), (4, '4 Stars'), (5, '5 Stars')],
        help_text="Rating out of 5 stars"
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Service Feedback'
        verbose_name_plural = 'Service Feedbacks'
        ordering = ['-created_at']

    def __str__(self):
        target = self.mechanic or self.workshop or "Provider"
        return f"Feedback for {target} by {self.customer.username} ({self.rating}★)"

