from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class SupplierProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        VERIFIED = 'VERIFIED', 'Verified'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='supplier_profile')
    business_name = models.CharField(max_length=200)
    business_address = models.TextField()
    phone_number = models.CharField(max_length=20)
    description = models.TextField(blank=True, default='')
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
        verbose_name = 'Supplier Profile'
        verbose_name_plural = 'Supplier Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.business_name} ({self.get_verification_status_display()})"

    @property
    def is_approved(self):
        """Check if supplier has active approved or verified status."""
        return self.verification_status in [
            self.VerificationStatus.APPROVED,
            self.VerificationStatus.VERIFIED,
        ]

    def get_total_revenue(self):
        """Calculate cumulative earnings exclusively from delivered/completed orders."""
        total = SparePartOrderItem.objects.filter(
            part__supplier=self,
            order__status=SparePartOrder.Status.DELIVERED
        ).aggregate(
            revenue=models.Sum(models.F('quantity') * models.F('unit_price'), output_field=models.DecimalField())
        )['revenue']
        return total or Decimal('0.00')

    def get_total_units_sold(self):
        """Calculate total number of item units sold in delivered orders."""
        total = SparePartOrderItem.objects.filter(
            part__supplier=self,
            order__status=SparePartOrder.Status.DELIVERED
        ).aggregate(units=models.Sum('quantity'))['units']
        return total or 0

    def get_total_stock(self):
        """Calculate aggregate warehouse inventory units across all products."""
        return self.spare_parts.aggregate(total=models.Sum('stock_quantity'))['total'] or 0

    def get_low_stock_count(self, threshold=5):
        """Count products with available inventory below or equal to the restock threshold."""
        return self.spare_parts.filter(stock_quantity__lte=threshold).count()


class SparePart(models.Model):
    supplier = models.ForeignKey(SupplierProfile, on_delete=models.CASCADE, related_name='spare_parts')
    part_name = models.CharField(max_length=200)
    part_number = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    compatible_manufacturer = models.CharField(max_length=100, blank=True, default='', help_text="e.g. Toyota, Honda, Ford")
    compatible_vehicle_models = models.TextField(help_text="Compatible vehicle makes/models")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='spare_parts/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Spare Part'
        verbose_name_plural = 'Spare Parts'
        ordering = ['part_name']

    def __str__(self):
        return f"{self.part_name} [{self.part_number}] - ${self.price}"

    @property
    def is_low_stock(self):
        return self.stock_quantity <= 5

    @property
    def in_stock(self):
        return self.stock_quantity > 0 and self.is_available


class SparePartOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        PROCESSING = 'PROCESSING', 'Processing'
        SHIPPED = 'SHIPPED', 'Shipped'
        DELIVERED = 'DELIVERED', 'Delivered'
        CANCELLED = 'CANCELLED', 'Cancelled'

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='spare_part_orders')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_address = models.TextField()
    contact_phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Spare Part Order'
        verbose_name_plural = 'Spare Part Orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.pk} by {self.customer.username} ({self.get_status_display()})"


class SparePartOrderItem(models.Model):
    order = models.ForeignKey(SparePartOrder, on_delete=models.CASCADE, related_name='items')
    part = models.ForeignKey(SparePart, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_deducted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Spare Part Order Item'
        verbose_name_plural = 'Spare Part Order Items'

    def __str__(self):
        return f"{self.quantity}x {self.part.part_name} for Order #{self.order.pk}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price
