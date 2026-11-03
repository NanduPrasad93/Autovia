from django.db import models
from django.contrib.auth.models import User


class Workshop(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workshops')
    workshop_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    address = models.TextField()
    phone_number = models.CharField(max_length=20)
    services_offered = models.TextField(help_text="Detailed services offered, e.g. body work, painting, engine overhaul")
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Workshop'
        verbose_name_plural = 'Workshops'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.workshop_name} ({self.get_verification_status_display()})"
