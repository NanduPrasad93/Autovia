from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        VEHICLE_OWNER = 'VEHICLE_OWNER', 'Vehicle Owner'
        MECHANIC = 'MECHANIC', 'Mechanic'
        WORKSHOP = 'WORKSHOP', 'Workshop'
        SUPPLIER = 'SUPPLIER', 'Supplier'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VEHICLE_OWNER,
        db_index=True,
    )
    phone_number = models.CharField(max_length=20, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_vehicle_owner(self):
        return self.role == self.Role.VEHICLE_OWNER

    @property
    def is_mechanic(self):
        return self.role == self.Role.MECHANIC

    @property
    def is_workshop(self):
        return self.role == self.Role.WORKSHOP

    @property
    def is_supplier(self):
        return self.role == self.Role.SUPPLIER


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        role = UserProfile.Role.ADMIN if instance.is_superuser else UserProfile.Role.VEHICLE_OWNER
        UserProfile.objects.get_or_create(user=instance, defaults={'role': role})


class Complaint(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints')
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Complaint'
        verbose_name_plural = 'Complaints'
        ordering = ['-created_at']

    def __str__(self):
        return f"Complaint #{self.pk}: {self.subject} ({self.get_status_display()}) by {self.user.username}"
