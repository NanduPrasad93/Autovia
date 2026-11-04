from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from decimal import Decimal

from accounts.models import UserProfile
from vehicles.models import Vehicle
from expenses.models import Expense
from expenses.forms import ExpenseForm


class VehicleExpenseTrackerTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'AutoVia@TestPass2026!'

        # User 1 (Vehicle Owner A)
        self.user_a = User.objects.create_user(
            username='owner_alice',
            email='alice@autovia.test',
            password=self.password,
            first_name='Alice',
            last_name='Automobile'
        )
        self.user_a.profile.role = UserProfile.Role.VEHICLE_OWNER
        self.user_a.profile.save()

        # User 2 (Vehicle Owner B)
        self.user_b = User.objects.create_user(
            username='owner_bob',
            email='bob@autovia.test',
            password=self.password,
            first_name='Bob',
            last_name='Brakes'
        )
        self.user_b.profile.role = UserProfile.Role.VEHICLE_OWNER
        self.user_b.profile.save()

        # Vehicles for User A
        self.vehicle_a1 = Vehicle.objects.create(
            owner=self.user_a,
            manufacturer='Toyota',
            model_name='RAV4 Hybrid',
            manufacturing_year=2022,
            registration_number='EXP-TEST-001',
            fuel_type='HYBRID',
            color='Silver',
            current_odometer=24000
        )
        self.vehicle_a2 = Vehicle.objects.create(
            owner=self.user_a,
            manufacturer='Tesla',
            model_name='Model 3',
            manufacturing_year=2023,
            registration_number='EXP-TEST-002',
            fuel_type='ELECTRIC',
            color='Pearl White',
            current_odometer=15000
        )

        # Vehicle for User B
        self.vehicle_b = Vehicle.objects.create(
            owner=self.user_b,
            manufacturer='Ford',
            model_name='F-150',
            manufacturing_year=2020,
            registration_number='BOB-TRUCK-99',
            fuel_type='PETROL',
            color='Shadow Black',
            current_odometer=55000
        )

        # Initial Expenses for User A
        self.expense_1 = Expense.objects.create(
            vehicle=self.vehicle_a1,
            owner=self.user_a,
            category=Expense.Category.FUEL,
            amount=Decimal('65.50'),
            description='Shell Super V-Power Fill-up 45 Liters',
            expense_date=timezone.now().date() - datetime.timedelta(days=10)
        )
        self.expense_2 = Expense.objects.create(
            vehicle=self.vehicle_a2,
            owner=self.user_a,
            category=Expense.Category.EV_CHARGING,
            amount=Decimal('28.00'),
            description='Supercharger 55kWh Fast DC Charging session',
            expense_date=timezone.now().date() - datetime.timedelta(days=5)
        )
        self.expense_3 = Expense.objects.create(
            vehicle=self.vehicle_a1,
            owner=self.user_a,
            category=Expense.Category.SERVICING,
            amount=Decimal('185.00'),
            description='20k Scheduled Synthetic Oil Service and Multipoint Check',
            expense_date=timezone.now().date() - datetime.timedelta(days=2)
        )

        # Initial Expense for User B
        self.expense_b = Expense.objects.create(
            vehicle=self.vehicle_b,
            owner=self.user_b,
            category=Expense.Category.REPAIR,
            amount=Decimal('420.00'),
            description='Alternator and serpentine belt replacement',
            expense_date=timezone.now().date() - datetime.timedelta(days=4)
        )

    # 1. Expense creation with positive amount validation
    def test_01_expense_creation_and_positive_validation(self):
        self.client.login(username='owner_alice', password=self.password)

        valid_data = {
            'vehicle': self.vehicle_a1.pk,
            'category': Expense.Category.INSURANCE,
            'amount': '350.00',
            'expense_date': timezone.now().date().isoformat(),
            'description': 'Comprehensive policy quarterly premium',
        }
        res = self.client.post(reverse('expenses:add'), valid_data, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "$350.00")
        self.assertTrue(Expense.objects.filter(description='Comprehensive policy quarterly premium').exists())

        # Zero or negative amount must be rejected
        invalid_data = valid_data.copy()
        invalid_data['amount'] = '-25.00'
        res_neg = self.client.post(reverse('expenses:add'), invalid_data)
        self.assertEqual(res_neg.status_code, 200)
        self.assertFormError(res_neg.context['form'], 'amount', 'Expense amount must be greater than zero.')

    # 2. Future dates must be rejected
    def test_02_expense_future_date_rejected(self):
        self.client.login(username='owner_alice', password=self.password)

        future_date = (timezone.now().date() + datetime.timedelta(days=10)).isoformat()
        future_data = {
            'vehicle': self.vehicle_a1.pk,
            'category': Expense.Category.FUEL,
            'amount': '50.00',
            'expense_date': future_date,
            'description': 'Future fuel',
        }
        res = self.client.post(reverse('expenses:add'), future_data)
        self.assertEqual(res.status_code, 200)
        self.assertFormError(res.context['form'], 'expense_date', 'Expense date cannot be set in the future.')

    # 3. Prevent logging an expense for another user's vehicle
    def test_03_prevent_logging_expense_for_another_users_vehicle(self):
        self.client.login(username='owner_alice', password=self.password)

        # Alice attempts to submit an expense against Bob's vehicle
        hijack_data = {
            'vehicle': self.vehicle_b.pk,
            'category': Expense.Category.REPAIR,
            'amount': '999.00',
            'expense_date': timezone.now().date().isoformat(),
            'description': 'Attempting unauthorized vehicle expense hijack',
        }
        res = self.client.post(reverse('expenses:add'), hijack_data)
        self.assertEqual(res.status_code, 200)
        # Form queryset validation or clean_vehicle rejects it
        self.assertFalse(res.context['form'].is_valid())
        self.assertFalse(Expense.objects.filter(description='Attempting unauthorized vehicle expense hijack').exists())

    # 4. Expense editing and strict ownership protection
    def test_04_expense_edit_and_ownership_protection(self):
        # Alice edits her own expense
        self.client.login(username='owner_alice', password=self.password)
        edit_url = reverse('expenses:edit', kwargs={'pk': self.expense_1.pk})

        res_get = self.client.get(edit_url)
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, "Shell Super V-Power")

        edit_data = {
            'vehicle': self.vehicle_a1.pk,
            'category': Expense.Category.FUEL,
            'amount': '72.25',
            'expense_date': self.expense_1.expense_date.isoformat(),
            'description': 'Updated: Shell V-Power 48 Liters fill-up',
        }
        res_post = self.client.post(edit_url, edit_data, follow=True)
        self.assertEqual(res_post.status_code, 200)
        self.expense_1.refresh_from_db()
        self.assertEqual(self.expense_1.amount, Decimal('72.25'))
        self.assertEqual(self.expense_1.description, 'Updated: Shell V-Power 48 Liters fill-up')
        self.client.logout()

        # Bob attempts to edit Alice's expense -> HTTP 404
        self.client.login(username='owner_bob', password=self.password)
        res_hack = self.client.get(edit_url)
        self.assertEqual(res_hack.status_code, 404)

        res_hack_post = self.client.post(edit_url, edit_data)
        self.assertEqual(res_hack_post.status_code, 404)

    # 5. Expense deletion and strict ownership protection
    def test_05_expense_delete_and_ownership_protection(self):
        delete_url = reverse('expenses:delete', kwargs={'pk': self.expense_3.pk})

        # Bob attempts to delete Alice's expense -> HTTP 404
        self.client.login(username='owner_bob', password=self.password)
        res_bob = self.client.post(delete_url)
        self.assertEqual(res_bob.status_code, 404)
        self.assertTrue(Expense.objects.filter(pk=self.expense_3.pk).exists())
        self.client.logout()

        # Alice deletes her own expense
        self.client.login(username='owner_alice', password=self.password)
        res_alice = self.client.post(delete_url, follow=True)
        self.assertEqual(res_alice.status_code, 200)
        self.assertFalse(Expense.objects.filter(pk=self.expense_3.pk).exists())

    # 6. Expense multi-criteria filtering
    def test_06_expense_filtering_by_category_vehicle_and_date(self):
        self.client.login(username='owner_alice', password=self.password)

        # Baseline list (shows both Alice's expenses, excludes Bob's)
        res_all = self.client.get(reverse('expenses:list'))
        self.assertEqual(res_all.status_code, 200)
        self.assertContains(res_all, "Shell Super V-Power")
        self.assertContains(res_all, "Supercharger 55kWh")
        self.assertNotContains(res_all, "Alternator and serpentine")

        # Filter by Category = EV_CHARGING
        res_cat = self.client.get(reverse('expenses:list'), {'category': Expense.Category.EV_CHARGING})
        self.assertEqual(res_cat.status_code, 200)
        self.assertContains(res_cat, "Supercharger 55kWh")
        self.assertNotContains(res_cat, "Shell Super V-Power")

        # Filter by Vehicle = Tesla Model 3
        res_veh = self.client.get(reverse('expenses:list'), {'vehicle_id': self.vehicle_a2.pk})
        self.assertEqual(res_veh.status_code, 200)
        self.assertContains(res_veh, "Supercharger 55kWh")
        self.assertNotContains(res_veh, "Shell Super V-Power")

        # Filter by Date range
        start = (timezone.now().date() - datetime.timedelta(days=6)).isoformat()
        end = timezone.now().date().isoformat()
        res_date = self.client.get(reverse('expenses:list'), {'start_date': start, 'end_date': end})
        self.assertEqual(res_date.status_code, 200)
        self.assertContains(res_date, "Supercharger 55kWh")
        self.assertNotContains(res_date, "Shell Super V-Power")

    # 7. Expense search by description
    def test_07_expense_search_by_description(self):
        self.client.login(username='owner_alice', password=self.password)

        res_search = self.client.get(reverse('expenses:list'), {'q': 'Supercharger'})
        self.assertEqual(res_search.status_code, 200)
        self.assertContains(res_search, "Supercharger 55kWh")
        self.assertNotContains(res_search, "Shell Super V-Power")

    # 8. Expense analytics dashboard calculations and Chart.js feeds
    def test_08_expense_analytics_dashboard_aggregates_and_charts(self):
        self.client.login(username='owner_alice', password=self.password)

        res = self.client.get(reverse('expenses:analytics'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Vehicle Expense Analytics & Intelligence")

        # Context aggregates check
        self.assertIn('total_filtered_expenses', res.context)
        self.assertIn('year_expenses_total', res.context)
        self.assertIn('top_category_name', res.context)
        self.assertIn('month_names_json', res.context)
        self.assertIn('monthly_trend_json', res.context)
        self.assertIn('cat_labels_json', res.context)
        self.assertIn('vehicle_labels_json', res.context)
        self.assertIn('yearly_labels_json', res.context)

        # Alice's total expenses: 65.50 + 28.00 + 185.00 = 278.50
        expected_total = Decimal('278.50')
        self.assertEqual(res.context['lifetime_total'], expected_total)

        # Most expensive category for Alice is SERVICING ($185.00)
        self.assertEqual(res.context['top_category_name'], 'Servicing')
        self.assertEqual(res.context['top_category_amount'], Decimal('185.00'))

    # 9. Expense CSV export format, headers, and active filters
    def test_09_expense_csv_export_format_and_filters(self):
        self.client.login(username='owner_alice', password=self.password)

        # Export all Alice's expenses
        res = self.client.get(reverse('expenses:export_csv'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="autovia_expenses_', res['Content-Disposition'])

        content = res.content.decode('utf-8')
        # Check CSV header row
        self.assertIn('Date,Vehicle,Registration Number,Category,Description,Amount ($ USD)', content)
        # Check rows
        self.assertIn('Shell Super V-Power Fill-up 45 Liters', content)
        self.assertIn('Supercharger 55kWh Fast DC Charging session', content)
        self.assertIn('20k Scheduled Synthetic Oil Service', content)
        # Bob's data must not be in Alice's CSV
        self.assertNotIn('BOB-TRUCK-99', content)
        self.assertNotIn('Alternator and serpentine', content)

        # Export with filter: category=EV_CHARGING
        res_filtered = self.client.get(reverse('expenses:export_csv'), {'category': Expense.Category.EV_CHARGING})
        self.assertEqual(res_filtered.status_code, 200)
        content_filt = res_filtered.content.decode('utf-8')
        self.assertIn('Supercharger 55kWh', content_filt)
        self.assertNotIn('Shell Super V-Power', content_filt)

    # 10. Cross-user isolation: user cannot export or view other user's records
    def test_10_cross_user_isolation_cannot_view_or_export_other_users_expenses(self):
        self.client.login(username='owner_bob', password=self.password)

        # Bob views his own list
        res_bob_list = self.client.get(reverse('expenses:list'))
        self.assertEqual(res_bob_list.status_code, 200)
        self.assertContains(res_bob_list, "Alternator and serpentine")
        self.assertNotContains(res_bob_list, "Shell Super V-Power")
        self.assertNotContains(res_bob_list, "Supercharger 55kWh")

        # Bob exports CSV
        res_bob_csv = self.client.get(reverse('expenses:export_csv'))
        self.assertEqual(res_bob_csv.status_code, 200)
        content_bob = res_bob_csv.content.decode('utf-8')
        self.assertIn('BOB-TRUCK-99', content_bob)
        self.assertNotIn('EXP-TEST-001', content_bob)
        self.assertNotIn('EXP-TEST-002', content_bob)
