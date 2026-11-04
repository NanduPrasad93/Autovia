from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import datetime

from accounts.models import UserProfile
from vehicles.models import Vehicle
from mechanics.models import MechanicProfile
from services.models import ServiceRequest, ServiceRecord
from expenses.models import Expense


class VehicleOwnerDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'OwnerSecurePass@2026'
        self.mechanic_password = 'MechanicPass@2026'

        # 1. Primary Vehicle Owner
        self.owner = User.objects.create_user(
            username='owner_jane',
            email='jane@autovia.test',
            password=self.password,
            first_name='Jane',
            last_name='Doe'
        )
        self.owner_profile = self.owner.profile
        self.owner_profile.role = UserProfile.Role.VEHICLE_OWNER
        self.owner_profile.phone_number = '+1-555-0199'
        self.owner_profile.address = '123 Auto Lane, Motortown'
        self.owner_profile.save()

        # 2. Secondary Vehicle Owner (for IDOR checks)
        self.owner2 = User.objects.create_user(
            username='owner_bob',
            email='bob@autovia.test',
            password=self.password,
            first_name='Bob',
            last_name='Smith'
        )
        self.owner2_profile = self.owner2.profile
        self.owner2_profile.role = UserProfile.Role.VEHICLE_OWNER
        self.owner2_profile.save()

        # 3. Mechanic User (for Role Check)
        self.mechanic_user = User.objects.create_user(
            username='tech_sam',
            email='sam@autovia.test',
            password=self.mechanic_password,
            first_name='Sam',
            last_name='Fixer'
        )
        self.mechanic_profile = self.mechanic_user.profile
        self.mechanic_profile.role = UserProfile.Role.MECHANIC
        self.mechanic_profile.save()
        self.mechanic_entry = MechanicProfile.objects.create(
            user=self.mechanic_user,
            specialization='Transmission & Powertrain',
            experience_years=8,
            service_location='East District',
            verification_status=MechanicProfile.VerificationStatus.VERIFIED
        )

        # Log in as primary owner by default
        self.client.login(username='owner_jane', password=self.password)

    # 1. Add vehicle
    def test_01_add_vehicle(self):
        url = reverse('vehicles:add')
        data = {
            'registration_number': 'KA-01-AB-1234',
            'manufacturer': 'Toyota',
            'model_name': 'Camry',
            'manufacturing_year': 2022,
            'fuel_type': 'HYBRID',
            'color': 'Pearl White',
            'current_odometer': 12500,
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('vehicles:list'))

        # Verify DB entry
        vehicle = Vehicle.objects.get(registration_number='KA-01-AB-1234')
        self.assertEqual(vehicle.owner, self.owner)
        self.assertEqual(vehicle.manufacturer, 'Toyota')
        self.assertEqual(vehicle.model_name, 'Camry')
        self.assertEqual(vehicle.current_odometer, 12500)

    # 2. Edit vehicle
    def test_02_edit_vehicle(self):
        vehicle = Vehicle.objects.create(
            owner=self.owner,
            registration_number='KA-02-CD-5678',
            manufacturer='Honda',
            model_name='Civic',
            manufacturing_year=2020,
            fuel_type=Vehicle.FuelType.PETROL,
            color='Silver',
            current_odometer=25000
        )
        url = reverse('vehicles:edit', kwargs={'pk': vehicle.pk})
        update_data = {
            'registration_number': 'KA-02-CD-5678',
            'manufacturer': 'Honda',
            'model_name': 'Civic Type-R',
            'manufacturing_year': 2020,
            'fuel_type': Vehicle.FuelType.PETROL,
            'color': 'Championship White',
            'current_odometer': 26500,
        }
        response = self.client.post(url, update_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('vehicles:detail', kwargs={'pk': vehicle.pk}))

        vehicle.refresh_from_db()
        self.assertEqual(vehicle.model_name, 'Civic Type-R')
        self.assertEqual(vehicle.color, 'Championship White')
        self.assertEqual(vehicle.current_odometer, 26500)

    # 3. Delete vehicle (POST only enforced)
    def test_03_delete_vehicle(self):
        vehicle = Vehicle.objects.create(
            owner=self.owner,
            registration_number='KA-03-EF-9012',
            manufacturer='Ford',
            model_name='Mustang',
            manufacturing_year=2019,
            fuel_type=Vehicle.FuelType.PETROL,
            color='Race Red',
            current_odometer=35000
        )
        delete_url = reverse('vehicles:delete', kwargs={'pk': vehicle.pk})

        # GET should be rejected (405 Method Not Allowed via @require_POST)
        res_get = self.client.get(delete_url)
        self.assertEqual(res_get.status_code, 405)
        self.assertTrue(Vehicle.objects.filter(pk=vehicle.pk).exists())

        # POST should successfully delete
        res_post = self.client.post(delete_url, follow=True)
        self.assertEqual(res_post.status_code, 200)
        self.assertRedirects(res_post, reverse('vehicles:list'))
        self.assertFalse(Vehicle.objects.filter(pk=vehicle.pk).exists())

    # 4. Register multiple vehicles
    def test_04_register_multiple_vehicles(self):
        v1 = Vehicle.objects.create(
            owner=self.owner,
            registration_number='MULTI-01',
            manufacturer='BMW',
            model_name='330i',
            manufacturing_year=2021,
            color='Blue',
            current_odometer=10000
        )
        v2 = Vehicle.objects.create(
            owner=self.owner,
            registration_number='MULTI-02',
            manufacturer='Audi',
            model_name='A4',
            manufacturing_year=2022,
            color='Black',
            current_odometer=15000
        )
        v3 = Vehicle.objects.create(
            owner=self.owner,
            registration_number='MULTI-03',
            manufacturer='Tesla',
            model_name='Model 3',
            manufacturing_year=2023,
            fuel_type=Vehicle.FuelType.ELECTRIC,
            color='Red',
            current_odometer=5000
        )

        response = self.client.get(reverse('vehicles:list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['vehicles'].count(), 3)
        self.assertContains(response, 'MULTI-01')
        self.assertContains(response, 'MULTI-02')
        self.assertContains(response, 'MULTI-03')

    # 5. Duplicate registration number validation
    def test_05_duplicate_registration_number_validation(self):
        Vehicle.objects.create(
            owner=self.owner2,
            registration_number='DUPLICATE-99',
            manufacturer='Nissan',
            model_name='Sentra',
            manufacturing_year=2020,
            color='Grey',
            current_odometer=50000
        )

        # Attempt to register vehicle with identical registration number (case-insensitive)
        data = {
            'registration_number': 'duplicate-99',
            'manufacturer': 'Mazda',
            'model_name': '3',
            'manufacturing_year': 2022,
            'fuel_type': 'PETROL',
            'color': 'Soul Red',
            'current_odometer': 12000,
        }
        response = self.client.post(reverse('vehicles:add'), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('registration_number', response.context['form'].errors)
        self.assertIn('already exists', response.context['form'].errors['registration_number'][0].lower())
        self.assertEqual(Vehicle.objects.filter(registration_number__iexact='duplicate-99').count(), 1)

    # 6. Create service request
    def test_06_create_service_request(self):
        vehicle = Vehicle.objects.create(
            owner=self.owner,
            registration_number='SR-1001',
            manufacturer='Hyundai',
            model_name='Tucson',
            manufacturing_year=2022,
            color='White',
            current_odometer=18000
        )

        url = reverse('services:request_create')
        future_date = (datetime.datetime.now() + datetime.timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'vehicle': vehicle.pk,
            'mechanic': self.mechanic_entry.pk,
            'problem_description': 'Unusual vibration during high-speed braking and steering drift.',
            'requested_date': future_date,
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Confirm ServiceRequest in database
        sr = ServiceRequest.objects.get(vehicle=vehicle, customer=self.owner)
        self.assertEqual(sr.mechanic, self.mechanic_entry)
        self.assertEqual(sr.status, ServiceRequest.Status.PENDING)
        self.assertContains(response, 'Unusual vibration during high-speed braking')

        # Test validation: cannot submit service request for vehicle not owned by user
        other_vehicle = Vehicle.objects.create(
            owner=self.owner2,
            registration_number='SR-OTHER-01',
            manufacturer='Kia',
            model_name='Sportage',
            manufacturing_year=2023,
            color='Silver',
            current_odometer=8000
        )
        invalid_data = {
            'vehicle': other_vehicle.pk,
            'problem_description': 'Unauthorized request test',
            'requested_date': future_date,
        }
        res_invalid = self.client.post(url, invalid_data)
        self.assertEqual(res_invalid.status_code, 200)
        self.assertIn('vehicle', res_invalid.context['form'].errors)

    # 7. View service history
    def test_07_view_service_history(self):
        vehicle = Vehicle.objects.create(
            owner=self.owner,
            registration_number='HIST-900',
            manufacturer='Subaru',
            model_name='Outback',
            manufacturing_year=2021,
            color='Forest Green',
            current_odometer=32000
        )
        record = ServiceRecord.objects.create(
            vehicle=vehicle,
            service_description='Replaced synthetic engine oil, cabin filter, and rotated all four tires.',
            service_date=datetime.date(2026, 10, 15),
            odometer_reading=30000,
            total_cost=Decimal('185.50')
        )

        res_list = self.client.get(reverse('services:history_list'))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, 'HIST-900')
        self.assertContains(res_list, '185.50')

        res_detail = self.client.get(reverse('services:record_detail', kwargs={'pk': record.pk}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, 'Replaced synthetic engine oil')

    # 8. Add expense
    def test_08_add_expense(self):
        vehicle = Vehicle.objects.create(
            owner=self.owner,
            registration_number='EXP-101',
            manufacturer='Volkswagen',
            model_name='Golf',
            manufacturing_year=2021,
            color='Tornado Red',
            current_odometer=21000
        )

        url = reverse('expenses:add')
        data = {
            'vehicle': vehicle.pk,
            'category': Expense.Category.FUEL,
            'amount': '62.50',
            'description': 'Full tank premium 95 unleaded at Shell',
            'expense_date': '2026-11-02',
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('expenses:list'))

        expense = Expense.objects.get(vehicle=vehicle, owner=self.owner)
        self.assertEqual(expense.amount, Decimal('62.50'))
        self.assertEqual(expense.category, Expense.Category.FUEL)

        # Test validation: zero or negative amount rejected
        invalid_data = {
            'vehicle': vehicle.pk,
            'category': Expense.Category.FUEL,
            'amount': '-15.00',
            'description': 'Negative amount invalid',
            'expense_date': '2026-11-02',
        }
        res_invalid = self.client.post(url, invalid_data)
        self.assertEqual(res_invalid.status_code, 200)
        self.assertIn('amount', res_invalid.context['form'].errors)

    # 9. View dashboard statistics
    def test_09_view_dashboard_statistics(self):
        # Setup 2 vehicles
        v1 = Vehicle.objects.create(
            owner=self.owner,
            registration_number='DASH-01',
            manufacturer='Volvo',
            model_name='XC60',
            manufacturing_year=2022,
            color='Denim Blue',
            current_odometer=14500
        )
        v2 = Vehicle.objects.create(
            owner=self.owner,
            registration_number='DASH-02',
            manufacturer='Mercedes-Benz',
            model_name='C300',
            manufacturing_year=2021,
            color='Obsidian Black',
            current_odometer=6500
        )

        # 1 pending service request
        ServiceRequest.objects.create(
            vehicle=v1,
            customer=self.owner,
            problem_description='Transmission inspection requested',
            requested_date=timezone.now() + datetime.timedelta(days=1),
            status=ServiceRequest.Status.PENDING
        )

        # 1 completed service record
        ServiceRecord.objects.create(
            vehicle=v1,
            service_description='Full 10,000 km routine maintenance package',
            service_date=datetime.date(2026, 9, 20),
            odometer_reading=10000,
            total_cost=Decimal('220.00')
        )

        # 2 expenses
        Expense.objects.create(
            vehicle=v1,
            owner=self.owner,
            category=Expense.Category.FUEL,
            amount=Decimal('80.00'),
            expense_date=datetime.date(2026, 11, 1)
        )
        Expense.objects.create(
            vehicle=v2,
            owner=self.owner,
            category=Expense.Category.SERVICING,
            amount=Decimal('120.00'),
            expense_date=datetime.date(2026, 11, 2)
        )

        response = self.client.get(reverse('accounts:vehicle_owner_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Check calculated metrics match DB values
        self.assertEqual(response.context['total_vehicles'], 2)
        self.assertEqual(response.context['pending_requests_count'], 1)
        self.assertEqual(response.context['completed_services_count'], 1)
        self.assertEqual(response.context['total_expenses'], Decimal('200.00'))

        # Check maintenance reminders generated for vehicles > 10,000 km and > 5,000 km
        reminders = response.context['maintenance_reminders']
        self.assertGreaterEqual(len(reminders), 2)

        # Check chart data present
        self.assertIn('category_labels_json', response.context)
        self.assertIn('monthly_labels_json', response.context)

    # 10. IDOR protection (accessing another user's vehicle returns 404)
    def test_10_idor_protection(self):
        other_vehicle = Vehicle.objects.create(
            owner=self.owner2,
            registration_number='OTHER-SECRET-77',
            manufacturer='Porsche',
            model_name='911',
            manufacturing_year=2023,
            color='Guards Red',
            current_odometer=4500
        )

        # Detail view should return 404
        res_detail = self.client.get(reverse('vehicles:detail', kwargs={'pk': other_vehicle.pk}))
        self.assertEqual(res_detail.status_code, 404)

        # Edit view should return 404
        res_edit = self.client.get(reverse('vehicles:edit', kwargs={'pk': other_vehicle.pk}))
        self.assertEqual(res_edit.status_code, 404)

        # Delete POST should return 404 and not delete
        res_delete = self.client.post(reverse('vehicles:delete', kwargs={'pk': other_vehicle.pk}))
        self.assertEqual(res_delete.status_code, 404)
        self.assertTrue(Vehicle.objects.filter(pk=other_vehicle.pk).exists())

    # 11. Role check (mechanic accessing vehicle owner dashboard returns 403)
    def test_11_role_based_access_control(self):
        # Switch session to mechanic user
        self.client.login(username='tech_sam', password=self.mechanic_password)

        # Vehicle Owner Dashboard -> 403 Forbidden
        res_dash = self.client.get(reverse('accounts:vehicle_owner_dashboard'))
        self.assertEqual(res_dash.status_code, 403)

        # Vehicle fleet list -> 403 Forbidden
        res_veh = self.client.get(reverse('vehicles:list'))
        self.assertEqual(res_veh.status_code, 403)

        # Vehicle expenses list -> 403 Forbidden
        res_exp = self.client.get(reverse('expenses:list'))
        self.assertEqual(res_exp.status_code, 403)

    # 12. Complete dashboard page load and response verification
    def test_12_dashboard_and_owner_pages_load(self):
        # Ensure logged in as vehicle owner
        self.client.login(username='owner_jane', password=self.password)

        vehicle = Vehicle.objects.create(
            owner=self.owner,
            registration_number='NAV-101',
            manufacturer='Lexus',
            model_name='RX350',
            manufacturing_year=2022,
            color='Caviar Black',
            current_odometer=16000
        )

        endpoints = [
            reverse('accounts:vehicle_owner_dashboard'),
            reverse('vehicles:list'),
            reverse('vehicles:add'),
            reverse('vehicles:detail', kwargs={'pk': vehicle.pk}),
            reverse('vehicles:edit', kwargs={'pk': vehicle.pk}),
            reverse('mechanics:find_mechanics'),
            reverse('services:request_list'),
            reverse('services:request_create'),
            reverse('services:history_list'),
            reverse('expenses:list'),
            reverse('expenses:add'),
            reverse('locations:nearby_stations'),
            reverse('locations:stations_api'),
            reverse('accounts:profile'),
            reverse('accounts:change_password'),
        ]

        for url in endpoints:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Endpoint {url} failed with status {res.status_code}")
