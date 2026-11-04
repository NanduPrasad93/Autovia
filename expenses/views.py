import csv
import json
import datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Q, Avg
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.utils import timezone

from accounts.decorators import vehicle_owner_required
from .models import Expense
from .forms import ExpenseForm
from vehicles.models import Vehicle


@vehicle_owner_required
def expense_list(request):
    """
    Display comprehensive vehicle expense tracker with statistics,
    multi-criteria filtering (vehicle, category, date range, search query),
    and transaction records.
    """
    user_expenses = Expense.objects.filter(owner=request.user).select_related('vehicle')

    # Query Parameters
    query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    vehicle_filter = request.GET.get('vehicle_id', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    filtered_qs = user_expenses

    if query:
        filtered_qs = filtered_qs.filter(
            Q(description__icontains=query) |
            Q(vehicle__registration_number__icontains=query) |
            Q(vehicle__model_name__icontains=query) |
            Q(vehicle__manufacturer__icontains=query)
        )

    if category_filter:
        filtered_qs = filtered_qs.filter(category=category_filter)

    if vehicle_filter:
        filtered_qs = filtered_qs.filter(vehicle_id=vehicle_filter)

    if start_date:
        try:
            start_d = datetime.date.fromisoformat(start_date)
            filtered_qs = filtered_qs.filter(expense_date__gte=start_d)
        except ValueError:
            pass

    if end_date:
        try:
            end_d = datetime.date.fromisoformat(end_date)
            filtered_qs = filtered_qs.filter(expense_date__lte=end_d)
        except ValueError:
            pass

    # Aggregates on filtered queryset
    total_spent = filtered_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_entries = filtered_qs.count()

    # Lifetime total for comparison
    lifetime_total = user_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Category breakdown for quick stats & Chart.js
    category_totals = (
        filtered_qs.values('category')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )

    category_map = dict(Expense.Category.choices)
    cat_labels = [category_map.get(item['category'], item['category']) for item in category_totals]
    cat_values = [float(item['total']) for item in category_totals]

    # Monthly breakdown (latest months in view)
    monthly_data = {}
    for exp in filtered_qs.order_by('expense_date'):
        month_key = exp.expense_date.strftime('%b %Y')
        monthly_data[month_key] = monthly_data.get(month_key, 0.0) + float(exp.amount)

    month_labels = list(monthly_data.keys())[-6:]
    month_values = [monthly_data[k] for k in month_labels]

    # Pagination
    paginator = Paginator(filtered_qs.order_by('-expense_date', '-created_at'), 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'expenses/expense_list.html', {
        'page_obj': page_obj,
        'expenses': page_obj.object_list,
        'total_spent': total_spent,
        'total_entries': total_entries,
        'lifetime_total': lifetime_total,
        'category_totals': category_totals,
        'category_map': category_map,
        'categories': Expense.Category.choices,
        'cat_labels_json': json.dumps(cat_labels),
        'cat_values_json': json.dumps(cat_values),
        'month_labels_json': json.dumps(month_labels),
        'month_values_json': json.dumps(month_values),
        'user_vehicles': request.user.vehicles.all(),
        'selected_vehicle_id': vehicle_filter,
        'selected_category': category_filter,
        'start_date': start_date,
        'end_date': end_date,
        'query': query,
        'page_title': 'Vehicle Expense Tracker | AutoVia',
    })


@vehicle_owner_required
def expense_add(request):
    """Log a new vehicle expense."""
    if not request.user.vehicles.exists():
        messages.warning(request, "Please register a vehicle before logging expenses.")
        return redirect('vehicles:add')

    initial_data = {}
    vehicle_id = request.GET.get('vehicle_id')
    if vehicle_id:
        vehicle = Vehicle.objects.filter(pk=vehicle_id, owner=request.user).first()
        if vehicle:
            initial_data['vehicle'] = vehicle

    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.owner = request.user
            expense.save()
            messages.success(request, f"Expense of ${expense.amount} for {expense.vehicle.registration_number} logged successfully.")
            return redirect('expenses:list')
    else:
        form = ExpenseForm(initial=initial_data, user=request.user)

    return render(request, 'expenses/expense_form.html', {
        'form': form,
        'is_edit': False,
        'page_title': 'Log Vehicle Expense | AutoVia',
    })


@vehicle_owner_required
def expense_edit(request, pk):
    """Edit an existing expense record with strict ownership isolation."""
    expense = get_object_or_404(Expense, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Expense entry #{expense.pk} updated successfully.")
            return redirect('expenses:list')
    else:
        form = ExpenseForm(instance=expense, user=request.user)

    return render(request, 'expenses/expense_form.html', {
        'form': form,
        'expense': expense,
        'is_edit': True,
        'page_title': f'Edit Expense #{expense.pk} | AutoVia',
    })


@vehicle_owner_required
@require_POST
def expense_delete(request, pk):
    """Delete an expense record with strict ownership isolation."""
    expense = get_object_or_404(Expense, pk=pk, owner=request.user)
    amount = expense.amount
    expense.delete()
    messages.success(request, f"Expense entry of ${amount} removed successfully.")
    return redirect('expenses:list')


@vehicle_owner_required
def expense_analytics(request):
    """
    Dedicated comprehensive analytics dashboard for vehicle owners.
    Calculates monthly, annual, per-vehicle, and category distributions
    using actual database records and supplies Chart.js data models.
    """
    user_expenses = Expense.objects.filter(owner=request.user).select_related('vehicle')

    # Available years from records
    expense_years = (
        user_expenses.dates('expense_date', 'year')
    )
    years_list = sorted({d.year for d in expense_years}, reverse=True)
    current_year = timezone.now().year
    if current_year not in years_list:
        years_list.insert(0, current_year)

    # Filter parameters
    selected_year = request.GET.get('year')
    if selected_year and selected_year.isdigit():
        selected_year = int(selected_year)
    else:
        selected_year = current_year

    selected_vehicle_id = request.GET.get('vehicle_id', '').strip()
    selected_category = request.GET.get('category', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    # Base filtered queryset for analytics
    analytics_qs = user_expenses

    if selected_vehicle_id:
        analytics_qs = analytics_qs.filter(vehicle_id=selected_vehicle_id)

    if selected_category:
        analytics_qs = analytics_qs.filter(category=selected_category)

    if start_date and end_date:
        try:
            s_d = datetime.date.fromisoformat(start_date)
            e_d = datetime.date.fromisoformat(end_date)
            analytics_qs = analytics_qs.filter(expense_date__range=[s_d, e_d])
        except ValueError:
            analytics_qs = analytics_qs.filter(expense_date__year=selected_year)
    else:
        analytics_qs = analytics_qs.filter(expense_date__year=selected_year)

    # 1. KPI Aggregates
    total_filtered_expenses = analytics_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Selected year total
    year_expenses_total = user_expenses.filter(expense_date__year=selected_year).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Current month total
    now = timezone.now()
    current_month_total = user_expenses.filter(
        expense_date__year=now.year,
        expense_date__month=now.month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Lifetime total
    lifetime_total = user_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Average monthly expense in selected year
    active_months_count = (
        user_expenses.filter(expense_date__year=selected_year)
        .dates('expense_date', 'month')
        .count()
    )
    if active_months_count > 0:
        avg_monthly_expense = year_expenses_total / Decimal(active_months_count)
    else:
        avg_monthly_expense = Decimal('0.00')

    # Most expensive category
    top_category_item = (
        analytics_qs.values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
        .first()
    )
    category_map = dict(Expense.Category.choices)
    if top_category_item:
        top_category_name = category_map.get(top_category_item['category'], top_category_item['category'])
        top_category_amount = top_category_item['total']
    else:
        top_category_name = "N/A"
        top_category_amount = Decimal('0.00')

    # 2. Chart A: 12-Month Expense Trend across selected year
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly_trend = [0.0] * 12

    year_filtered_records = user_expenses.filter(expense_date__year=selected_year)
    if selected_vehicle_id:
        year_filtered_records = year_filtered_records.filter(vehicle_id=selected_vehicle_id)
    if selected_category:
        year_filtered_records = year_filtered_records.filter(category=selected_category)

    for exp in year_filtered_records:
        idx = exp.expense_date.month - 1
        monthly_trend[idx] += float(exp.amount)

    # 3. Chart B: Category Breakdown (Doughnut)
    cat_distribution = (
        analytics_qs.values('category')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )
    cat_labels = [category_map.get(item['category'], item['category']) for item in cat_distribution]
    cat_values = [float(item['total']) for item in cat_distribution]

    # Category Breakdown Table with percentages
    category_table_data = []
    for item in cat_distribution:
        amt = item['total']
        pct = (amt / total_filtered_expenses * 100) if total_filtered_expenses > 0 else Decimal('0.0')
        category_table_data.append({
            'code': item['category'],
            'label': category_map.get(item['category'], item['category']),
            'count': item['count'],
            'total': amt,
            'percentage': round(pct, 1),
        })

    # 4. Chart C: Vehicle Comparison (Bar)
    user_vehicles = request.user.vehicles.all()
    vehicle_labels = []
    vehicle_values = []
    vehicle_summary_table = []

    for v in user_vehicles:
        v_spend = user_expenses.filter(vehicle=v).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        v_count = user_expenses.filter(vehicle=v).count()
        v_label = f"{v.manufacturer} {v.model_name} ({v.registration_number})"
        vehicle_labels.append(v_label)
        vehicle_values.append(float(v_spend))

        v_pct = (v_spend / lifetime_total * 100) if lifetime_total > 0 else Decimal('0.0')
        vehicle_summary_table.append({
            'vehicle': v,
            'count': v_count,
            'total': v_spend,
            'percentage': round(v_pct, 1),
        })

    # 5. Chart D: Yearly Summary (Historical comparison)
    yearly_labels = []
    yearly_values = []
    yearly_table = []

    for yr in sorted(years_list):
        yr_spend = user_expenses.filter(expense_date__year=yr).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        yr_count = user_expenses.filter(expense_date__year=yr).count()
        yearly_labels.append(str(yr))
        yearly_values.append(float(yr_spend))
        yearly_table.append({
            'year': yr,
            'count': yr_count,
            'total': yr_spend,
        })

    yearly_table.reverse()

    return render(request, 'expenses/analytics.html', {
        'page_title': 'Vehicle Expense Analytics & Reports | AutoVia',
        'years_list': years_list,
        'selected_year': selected_year,
        'user_vehicles': user_vehicles,
        'categories': Expense.Category.choices,
        'selected_vehicle_id': selected_vehicle_id,
        'selected_category': selected_category,
        'start_date': start_date,
        'end_date': end_date,
        # KPIs
        'total_filtered_expenses': total_filtered_expenses,
        'year_expenses_total': year_expenses_total,
        'current_month_total': current_month_total,
        'avg_monthly_expense': avg_monthly_expense,
        'lifetime_total': lifetime_total,
        'top_category_name': top_category_name,
        'top_category_amount': top_category_amount,
        # Chart JSON data
        'month_names_json': json.dumps(month_names),
        'monthly_trend_json': json.dumps(monthly_trend),
        'cat_labels_json': json.dumps(cat_labels),
        'cat_values_json': json.dumps(cat_values),
        'vehicle_labels_json': json.dumps(vehicle_labels),
        'vehicle_values_json': json.dumps(vehicle_values),
        'yearly_labels_json': json.dumps(yearly_labels),
        'yearly_values_json': json.dumps(yearly_values),
        # Table data
        'category_table_data': category_table_data,
        'vehicle_summary_table': vehicle_summary_table,
        'yearly_table': yearly_table,
    })


@vehicle_owner_required
def expense_export_csv(request):
    """
    Export vehicle expenses to a CSV file.
    Respects active user filters (vehicle, category, date range, search)
    and strictly isolates export records to the authenticated user.
    """
    user_expenses = Expense.objects.filter(owner=request.user).select_related('vehicle')

    # Query Filters
    query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    vehicle_filter = request.GET.get('vehicle_id', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    filtered_qs = user_expenses

    if query:
        filtered_qs = filtered_qs.filter(
            Q(description__icontains=query) |
            Q(vehicle__registration_number__icontains=query) |
            Q(vehicle__model_name__icontains=query) |
            Q(vehicle__manufacturer__icontains=query)
        )

    if category_filter:
        filtered_qs = filtered_qs.filter(category=category_filter)

    if vehicle_filter:
        filtered_qs = filtered_qs.filter(vehicle_id=vehicle_filter)

    if start_date:
        try:
            start_d = datetime.date.fromisoformat(start_date)
            filtered_qs = filtered_qs.filter(expense_date__gte=start_d)
        except ValueError:
            pass

    if end_date:
        try:
            end_d = datetime.date.fromisoformat(end_date)
            filtered_qs = filtered_qs.filter(expense_date__lte=end_d)
        except ValueError:
            pass

    filtered_qs = filtered_qs.order_by('-expense_date', '-created_at')

    timestamp_str = timezone.now().strftime('%Y%m%d_%H%M%S')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="autovia_expenses_{timestamp_str}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Date',
        'Vehicle',
        'Registration Number',
        'Category',
        'Description',
        'Amount ($ USD)'
    ])

    total_amount = Decimal('0.00')
    for exp in filtered_qs:
        total_amount += exp.amount
        writer.writerow([
            exp.expense_date.strftime('%Y-%m-%d'),
            f"{exp.vehicle.manufacturer} {exp.vehicle.model_name}",
            exp.vehicle.registration_number,
            exp.get_category_display(),
            exp.description.replace('\n', ' ') if exp.description else '',
            f"{exp.amount:.2f}",
        ])

    writer.writerow([])
    writer.writerow(['Total Amount', '', '', '', '', f"{total_amount:.2f}"])
    writer.writerow(['Total Records', '', '', '', '', filtered_qs.count()])

    return response
