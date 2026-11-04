from django.db import models
from django.contrib.auth.models import User


class Workshop(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        VERIFIED = 'VERIFIED', 'Verified'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workshops')
    workshop_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    address = models.TextField()
    phone_number = models.CharField(max_length=20)
    services_offered = models.TextField(help_text="Detailed services offered, e.g. body work, painting, engine overhaul")
    workshop_image = models.ImageField(upload_to='workshops/', blank=True, null=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )
    rejection_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Workshop'
        verbose_name_plural = 'Workshops'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.workshop_name} ({self.get_verification_status_display()})"

    @property
    def is_approved(self):
        """Check if workshop has active approved or verified status."""
        return self.verification_status in [
            self.VerificationStatus.APPROVED,
            self.VerificationStatus.VERIFIED,
        ]

    def get_average_rating(self):
        """Compute average customer rating from verified feedbacks."""
        avg = self.feedbacks.aggregate(models.Avg('rating'))['rating__avg']
        return round(avg, 1) if avg is not None else 0.0

    def get_total_revenue(self):
        """Compute cumulative earnings from issued repair bills."""
        from decimal import Decimal
        total = self.owner.issued_repair_bills.filter(
            service_request__workshop=self
        ).aggregate(models.Sum('total_amount'))['total_amount__sum']
        return total or Decimal('0.00')
