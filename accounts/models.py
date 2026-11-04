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
        REJECTED = 'REJECTED', 'Rejected'
        CLOSED = 'CLOSED', 'Closed'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints')
    service_request = models.ForeignKey(
        'services.ServiceRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='complaints'
    )
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    admin_response = models.TextField(blank=True, default='')
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_complaints'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Complaint'
        verbose_name_plural = 'Complaints'
        ordering = ['-created_at']

    def __str__(self):
        return f"Complaint #{self.pk}: {self.subject} ({self.get_status_display()}) by {self.user.username}"


class ActivityLog(models.Model):
    class ActionType(models.TextChoices):
        USER_STATUS = 'USER_STATUS', 'User Status Update'
        USER_REGISTRATION = 'USER_REGISTRATION', 'User Registration'
        MECHANIC_VERIFICATION = 'MECHANIC_VERIFICATION', 'Mechanic Verification'
        WORKSHOP_VERIFICATION = 'WORKSHOP_VERIFICATION', 'Workshop Verification'
        SUPPLIER_VERIFICATION = 'SUPPLIER_VERIFICATION', 'Supplier Verification'
        SERVICE_REQUEST_UPDATE = 'SERVICE_REQUEST_UPDATE', 'Service Request Update'
        COMPLAINT_UPDATE = 'COMPLAINT_UPDATE', 'Complaint Update'
        ADMIN_ACTION = 'ADMIN_ACTION', 'General Admin Action'

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs'
    )
    action_type = models.CharField(
        max_length=50,
        choices=ActionType.choices,
        default=ActionType.ADMIN_ACTION,
        db_index=True
    )
    description = models.TextField()
    target_content_type = models.CharField(max_length=100, blank=True, default='')
    target_object_id = models.CharField(max_length=100, blank=True, default='')
    target_repr = models.CharField(max_length=255, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        ordering = ['-created_at']

    def __str__(self):
        actor = self.user.username if self.user else 'System'
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {actor}: {self.description[:50]}"


def log_activity(user, action_type, description, target=None, ip_address=None):
    """Safely records platform administrative actions with actor, target, and timestamp."""
    target_content_type = ''
    target_object_id = ''
    target_repr = ''
    if target is not None:
        target_content_type = target.__class__.__name__
        target_object_id = str(getattr(target, 'pk', ''))
        target_repr = str(target)[:255]

    actor = user if (user and getattr(user, 'is_authenticated', False)) else None
    return ActivityLog.objects.create(
        user=actor,
        action_type=action_type,
        description=description,
        target_content_type=target_content_type,
        target_object_id=target_object_id,
        target_repr=target_repr,
        ip_address=ip_address,
    )

