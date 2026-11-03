from django.db import models
from django.contrib.auth.models import User


class MechanicProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mechanic_profile')
    specialization = models.CharField(max_length=200, help_text="e.g. Engine, Brakes, Transmission, Electrical")
    experience_years = models.PositiveIntegerField(default=0)
    service_location = models.CharField(max_length=255, help_text="Primary area or city of service")
    description = models.TextField(blank=True)
    is_available = models.BooleanField(default=True, db_index=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Mechanic Profile'
        verbose_name_plural = 'Mechanic Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.specialization} ({self.get_verification_status_display()})"
