import json
import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction, models
from django.db.models import Q, Sum, F, Count
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from accounts.decorators import supplier_required
from accounts.models import UserProfile
from .models import SupplierProfile, SparePart, SparePartOrder, SparePartOrderItem
from .forms import SupplierProfileForm, SparePartForm


def get_supplier_profile_for_user(user):
    """Retrieve or safely create the SupplierProfile entity for the authenticated supplier user."""
    profile = getattr(user, 'supplier_profile', None)
    if not profile:
        profile, _ = SupplierProfile.objects.get_or_create(
            user=user,
            defaults={
                'business_name': f"{user.get_full_name() or user.username}'s Auto Supplies",
                'business_address': getattr(user, 'profile', None).address if hasattr(user, 'profile') and user.profile.address else 'Warehouse address pending update',
                'phone_number': getattr(user, 'profile', None).phone_number if hasattr(user, 'profile') and user.profile.phone_number else '+1-555-000-0000',
                'description': 'Automotive replacement components and genuine OEM spare parts distributor.',
                'verification_status': SupplierProfile.VerificationStatus.PENDING,
            }
        )
    return profile


# -------------------------------------------------------------
# 1. Supplier Dashboard Overview
# -------------------------------------------------------------

@supplier_required
def supplier_dashboard(request):
    """
    Main Supplier Dashboard displaying live inventory volume, available stock,
    pending orders, delivered sales revenue, low-stock warnings, and recent activity.
    """
    supplier = get_supplier_profile_for_user(request.user)

    # 1. Database Aggregations
    total_products = supplier.spare_parts.count()
    available_stock = supplier.get_total_stock()
    low_stock_count = supplier.get_low_stock_count(threshold=5)

    supplier_orders = SparePartOrder.objects.filter(
        items__part__supplier=supplier
    ).distinct()

    pending_orders = supplier_orders.filter(status=SparePartOrder.Status.PENDING).count()
    active_fulfillment = supplier_orders.filter(
        status__in=[SparePartOrder.Status.CONFIRMED, SparePartOrder.Status.PROCESSING, SparePartOrder.Status.SHIPPED]
    ).count()
    completed_orders = supplier_orders.filter(status=SparePartOrder.Status.DELIVERED).count()

    total_revenue = supplier.get_total_revenue()
    total_units_sold = supplier.get_total_units_sold()

    # 2. Alerts & Activity
    low_stock_products = supplier.spare_parts.filter(
        stock_quantity__lte=5
    ).order_by('stock_quantity')[:5]

    recent_orders = supplier_orders.select_related('customer').order_by('-created_at')[:6]

    # 3. Monthly Sales Trend (Past 6 Months)
    today = datetime.date.today()
    monthly_labels = []
    monthly_revenue = []
    monthly_units = []

    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        label = datetime.date(year, month, 1).strftime('%b %Y')

        rev = SparePartOrderItem.objects.filter(
            part__supplier=supplier,
            order__status=SparePartOrder.Status.DELIVERED,
            order__updated_at__year=year,
            order__updated_at__month=month
        ).aggregate(
            revenue=Sum(F('quantity') * F('unit_price'), output_field=models.DecimalField())
        )['revenue'] or Decimal('0.00')

        units = SparePartOrderItem.objects.filter(
            part__supplier=supplier,
            order__status=SparePartOrder.Status.DELIVERED,
            order__updated_at__year=year,
            order__updated_at__month=month
        ).aggregate(total=Sum('quantity'))['total'] or 0

        monthly_labels.append(label)
        monthly_revenue.append(float(rev))
        monthly_units.append(units)

    context = {
        'supplier': supplier,
        'page_title': f"{supplier.business_name} | Supplier Dashboard",
        'total_products': total_products,
        'available_stock': available_stock,
        'low_stock_count': low_stock_count,
        'pending_orders': pending_orders,
        'active_fulfillment': active_fulfillment,
        'completed_orders': completed_orders,
        'total_revenue': total_revenue,
        'total_units_sold': total_units_sold,
        'low_stock_products': low_stock_products,
        'recent_orders': recent_orders,
        'monthly_labels_json': json.dumps(monthly_labels),
        'monthly_revenue_json': json.dumps(monthly_revenue),
        'monthly_units_json': json.dumps(monthly_units),
    }
    return render(request, 'suppliers/dashboard.html', context)


# -------------------------------------------------------------
# 2. Supplier Profile Management
# -------------------------------------------------------------

@supplier_required
def supplier_profile(request):
    """View and update supplier business name, contact details, email, and facility address."""
    supplier = get_supplier_profile_for_user(request.user)

    if request.method == 'POST':
        form = SupplierProfileForm(request.POST, instance=supplier)
        if form.is_valid():
            prof = form.save(commit=False)
            prof.user = request.user
            # Ensure verification_status is preserved exactly from database
            prof.verification_status = supplier.verification_status
            prof.save()

            # Update user email
            contact_email = form.cleaned_data.get('contact_email')
            if contact_email and contact_email != request.user.email:
                request.user.email = contact_email
                request.user.save()

            messages.success(request, "Supplier business profile details updated successfully.")
            return redirect('suppliers:profile')
        else:
            messages.error(request, "Please correct the form errors below.")
    else:
        form = SupplierProfileForm(instance=supplier)

    return render(request, 'suppliers/profile.html', {
        'supplier': supplier,
        'form': form,
        'page_title': 'Supplier Business Profile | AutoVia',
    })


@supplier_required
def verification_status_view(request):
    """Dedicated screen explaining supplier trade licensing and verification status."""
    supplier = get_supplier_profile_for_user(request.user)
    return render(request, 'suppliers/verification.html', {
        'supplier': supplier,
        'page_title': 'Supplier Verification Status | AutoVia',
    })


# -------------------------------------------------------------
# 3. Spare Parts Product & Inventory Management
# -------------------------------------------------------------

@supplier_required
def product_list(request):
    """Browse, search, filter, and sort catalog products."""
    supplier = get_supplier_profile_for_user(request.user)

    query = request.GET.get('q', '').strip()
    stock_filter = request.GET.get('stock', '').strip()
    mfg_filter = request.GET.get('mfg', '').strip()
    sort_by = request.GET.get('sort', 'name').strip()

    products = supplier.spare_parts.all()

    if query:
        products = products.filter(
            Q(part_name__icontains=query) |
            Q(part_number__icontains=query) |
            Q(compatible_manufacturer__icontains=query) |
            Q(compatible_vehicle_models__icontains=query) |
            Q(description__icontains=query)
        )

    if mfg_filter:
        products = products.filter(compatible_manufacturer__icontains=mfg_filter)

    if stock_filter == 'low':
        products = products.filter(stock_quantity__lte=5, stock_quantity__gt=0)
    elif stock_filter == 'out':
        products = products.filter(stock_quantity=0)
    elif stock_filter == 'in':
        products = products.filter(stock_quantity__gt=0)

    # Sorting
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'stock_asc':
        products = products.order_by('stock_quantity')
    elif sort_by == 'stock_desc':
        products = products.order_by('-stock_quantity')
    else:
        products = products.order_by('part_name')

    manufacturers = supplier.spare_parts.exclude(
        compatible_manufacturer=''
    ).values_list('compatible_manufacturer', flat=True).distinct()

    return render(request, 'suppliers/products.html', {
        'supplier': supplier,
        'products': products,
        'query': query,
        'stock_filter': stock_filter,
        'mfg_filter': mfg_filter,
        'sort_by': sort_by,
        'manufacturers': manufacturers,
        'page_title': 'Spare Parts Catalog | AutoVia',
    })


@supplier_required
def product_add(request):
    """Add a new spare part to the catalog. Restricted to approved suppliers."""
    supplier = get_supplier_profile_for_user(request.user)

    if not supplier.is_approved:
        messages.error(request, "Your supplier business registration must be approved before you can list new products.")
        return redirect('suppliers:products')

    if request.method == 'POST':
        form = SparePartForm(request.POST, request.FILES)
        if form.is_valid():
            part = form.save(commit=False)
            part.supplier = supplier
            part.save()
            messages.success(request, f"Spare Part '{part.part_name}' ({part.part_number}) has been listed successfully.")
            return redirect('suppliers:products')
        else:
            messages.error(request, "Please check the product fields and validation errors.")
    else:
        form = SparePartForm()

    return render(request, 'suppliers/product_form.html', {
        'supplier': supplier,
        'form': form,
        'is_edit': False,
        'page_title': 'Add New Spare Part | AutoVia',
    })


@supplier_required
def product_edit(request, pk):
    """Edit an existing spare part. Strictly scoped to supplier."""
    supplier = get_supplier_profile_for_user(request.user)
    part = get_object_or_404(SparePart, pk=pk, supplier=supplier)

    if request.method == 'POST':
        form = SparePartForm(request.POST, request.FILES, instance=part)
        if form.is_valid():
            part = form.save(commit=False)
            part.supplier = supplier
            part.save()
            messages.success(request, f"Product '{part.part_name}' details updated successfully.")
            return redirect('suppliers:products')
        else:
            messages.error(request, "Please correct the errors indicated below.")
    else:
        form = SparePartForm(instance=part)

    return render(request, 'suppliers/product_form.html', {
        'supplier': supplier,
        'form': form,
        'part': part,
        'is_edit': True,
        'page_title': f"Edit {part.part_name} | AutoVia",
    })


@supplier_required
@require_POST
def product_delete(request, pk):
    """Delete a product when it is not involved in active orders."""
    supplier = get_supplier_profile_for_user(request.user)
    part = get_object_or_404(SparePart, pk=pk, supplier=supplier)

    # Check if part is involved in active orders (PENDING, CONFIRMED, PROCESSING, SHIPPED)
    active_orders = part.order_items.filter(
        order__status__in=[
            SparePartOrder.Status.PENDING,
            SparePartOrder.Status.CONFIRMED,
            SparePartOrder.Status.PROCESSING,
            SparePartOrder.Status.SHIPPED,
        ]
    )

    if active_orders.exists():
        messages.error(request, f"Cannot delete '{part.part_name}' because it is part of active orders currently undergoing fulfillment.")
        return redirect('suppliers:products')

    try:
        part_name = part.part_name
        part.delete()
        messages.success(request, f"Product '{part_name}' has been deleted from catalog.")
    except Exception as e:
        messages.error(request, f"Could not delete product: {str(e)}")

    return redirect('suppliers:products')


@supplier_required
def inventory_management(request):
    """Dedicated inventory stock tracking console highlighting low-stock and reorder SKUs."""
    supplier = get_supplier_profile_for_user(request.user)

    low_stock = supplier.spare_parts.filter(stock_quantity__lte=5, stock_quantity__gt=0).order_by('stock_quantity')
    out_of_stock = supplier.spare_parts.filter(stock_quantity=0).order_by('part_name')
    adequate_stock = supplier.spare_parts.filter(stock_quantity__gt=5).order_by('part_name')

    total_stock = supplier.get_total_stock()
    total_skus = supplier.spare_parts.count()

    return render(request, 'suppliers/inventory.html', {
        'supplier': supplier,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'adequate_stock': adequate_stock,
        'total_stock': total_stock,
        'total_skus': total_skus,
        'page_title': 'Inventory & Stock Management | AutoVia',
    })


# -------------------------------------------------------------
# 4. Order Management & Safe Stock Integrity
# -------------------------------------------------------------

@supplier_required
def order_list(request):
    """View incoming purchase orders containing products from this supplier."""
    supplier = get_supplier_profile_for_user(request.user)

    status_filter = request.GET.get('status', '').strip()

    orders = SparePartOrder.objects.filter(
        items__part__supplier=supplier
    ).distinct().select_related('customer')

    if status_filter:
        orders = orders.filter(status=status_filter)

    orders = orders.order_by('-created_at')

    return render(request, 'suppliers/orders.html', {
        'supplier': supplier,
        'orders': orders,
        'status_filter': status_filter,
        'page_title': 'Purchase Orders | AutoVia',
    })


@supplier_required
def order_detail(request, pk):
    """
    Inspect purchase order details, customer shipping destination,
    and items supplied by this specific supplier.
    """
    supplier = get_supplier_profile_for_user(request.user)

    order = get_object_or_404(
        SparePartOrder.objects.prefetch_related('items__part'),
        items__part__supplier=supplier,
        pk=pk
    )

    # Filter items to only those belonging to this supplier
    supplier_items = order.items.filter(part__supplier=supplier).select_related('part')
    supplier_subtotal = sum((item.subtotal for item in supplier_items), Decimal('0.00'))

    return render(request, 'suppliers/order_detail.html', {
        'supplier': supplier,
        'order': order,
        'supplier_items': supplier_items,
        'supplier_subtotal': supplier_subtotal,
        'page_title': f"Order #{order.pk} Details | AutoVia",
    })


@supplier_required
@require_POST
def update_order_status(request, pk):
    """
    Progress order status with strict atomic stock integrity:
    PENDING -> CONFIRMED -> PROCESSING -> SHIPPED -> DELIVERED (or CANCELLED).
    Deducts inventory safely upon confirmation; restores inventory if cancelled.
    """
    supplier = get_supplier_profile_for_user(request.user)

    if not supplier.is_approved:
        messages.error(request, "Supplier approval is required to process and fulfill customer orders.")
        return redirect('suppliers:order_detail', pk=pk)

    new_status = request.POST.get('status')
    valid_statuses = [
        SparePartOrder.Status.CONFIRMED,
        SparePartOrder.Status.PROCESSING,
        SparePartOrder.Status.SHIPPED,
        SparePartOrder.Status.DELIVERED,
        SparePartOrder.Status.CANCELLED,
    ]

    if new_status not in valid_statuses:
        messages.error(request, "Invalid order status requested.")
        return redirect('suppliers:order_detail', pk=pk)

    with transaction.atomic():
        try:
            order = SparePartOrder.objects.select_for_update().get(
                items__part__supplier=supplier,
                pk=pk
            )
        except SparePartOrder.DoesNotExist:
            raise Http404("The specified purchase order was not found or does not contain parts from your catalog.")

        supplier_items = order.items.select_related('part').filter(part__supplier=supplier)

        # 1. Action: Confirming Order -> Safe Stock Deduction
        if new_status in [SparePartOrder.Status.CONFIRMED, SparePartOrder.Status.PROCESSING]:
            for item in supplier_items:
                if not item.stock_deducted:
                    part = SparePart.objects.select_for_update().get(pk=item.part_id)
                    if part.stock_quantity < item.quantity:
                        messages.error(
                            request,
                            f"Insufficient stock for '{part.part_name}' (SKU: {part.part_number}). "
                            f"Requested: {item.quantity}, Available in stock: {part.stock_quantity}. "
                            f"Order confirmation aborted."
                        )
                        return redirect('suppliers:order_detail', pk=order.pk)
                    # Deduct stock safely
                    part.stock_quantity -= item.quantity
                    part.save()
                    item.stock_deducted = True
                    item.save()

        # 2. Action: Cancelling Order -> Safe Stock Restoration
        elif new_status == SparePartOrder.Status.CANCELLED:
            for item in supplier_items:
                if item.stock_deducted:
                    part = SparePart.objects.select_for_update().get(pk=item.part_id)
                    # Restore stock safely
                    part.stock_quantity += item.quantity
                    part.save()
                    item.stock_deducted = False
                    item.save()

        # Update order status
        order.status = new_status
        order.save()

    messages.success(request, f"Order #{order.pk} status updated to: {order.get_status_display()}.")
    return redirect('suppliers:order_detail', pk=order.pk)


# -------------------------------------------------------------
# 5. Sales & Financial Reports
# -------------------------------------------------------------

@supplier_required
def sales_reports(request):
    """
    Supplier Sales & Performance Dashboard.
    Calculates revenue, units sold, and best-selling products exclusively
    from delivered/completed orders.
    """
    supplier = get_supplier_profile_for_user(request.user)

    total_revenue = supplier.get_total_revenue()
    total_units_sold = supplier.get_total_units_sold()

    completed_orders = SparePartOrder.objects.filter(
        items__part__supplier=supplier,
        status=SparePartOrder.Status.DELIVERED
    ).distinct()

    total_completed_orders = completed_orders.count()

    # Best-selling products
    best_sellers = supplier.spare_parts.filter(
        order_items__order__status=SparePartOrder.Status.DELIVERED
    ).annotate(
        units_sold=Sum('order_items__quantity'),
        sales_volume=Sum(F('order_items__quantity') * F('order_items__unit_price'))
    ).order_by('-units_sold')[:5]

    # Recent completed orders
    recent_completed = completed_orders.select_related('customer').order_by('-updated_at')[:5]

    # Monthly Sales Chart Data (Past 6 Months)
    today = datetime.date.today()
    monthly_labels = []
    monthly_revenue = []
    monthly_orders = []

    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        label = datetime.date(year, month, 1).strftime('%b %Y')

        rev = SparePartOrderItem.objects.filter(
            part__supplier=supplier,
            order__status=SparePartOrder.Status.DELIVERED,
            order__updated_at__year=year,
            order__updated_at__month=month
        ).aggregate(
            revenue=Sum(F('quantity') * F('unit_price'), output_field=models.DecimalField())
        )['revenue'] or Decimal('0.00')

        orders_count = completed_orders.filter(
            updated_at__year=year,
            updated_at__month=month
        ).count()

        monthly_labels.append(label)
        monthly_revenue.append(float(rev))
        monthly_orders.append(orders_count)

    context = {
        'supplier': supplier,
        'page_title': 'Sales & Financial Reports | AutoVia',
        'total_revenue': total_revenue,
        'total_units_sold': total_units_sold,
        'total_completed_orders': total_completed_orders,
        'best_sellers': best_sellers,
        'recent_completed': recent_completed,
        'monthly_labels_json': json.dumps(monthly_labels),
        'monthly_revenue_json': json.dumps(monthly_revenue),
        'monthly_orders_json': json.dumps(monthly_orders),
    }
    return render(request, 'suppliers/sales.html', context)
