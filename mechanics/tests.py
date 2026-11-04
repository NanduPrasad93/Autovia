from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import datetime

from accounts.models import UserProfile
from mechanics.models import MechanicProfile
from vehicles.models import Vehicle
from services.models import ServiceRequest, RepairEstimate, RepairBill, ServiceRecord, ServiceFeedback


class MechanicDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.mechanic_password = 'MechanicPass@2026'
        self.owner_password = 'OwnerPass@2026'

        # 1. Primary Verified Mechanic
        self.mechanic_user = User.objects.create_user(
            username='tech_alex',
            email='alex@autovia.test',
            password=self.mechanic_password,
            first_name='Alex',
            last_name='Vance'
        )
        self.mechanic_profile = self.mechanic_user.profile
        self.mechanic_profile.role = UserProfile.Role.MECHANIC
        self.mechanic_profile.phone_number = '+1-555-0101'
        self.mechanic_profile.save()

        self.mechanic = MechanicProfile.objects.create(
            user=self.mechanic_user,
            specialization='Diagnostics & Engine Repair',
            experience_years=7,
            service_location='West Metro District',
            description='ASE certified technician with diagnostic scan equipment.',
            is_available=True,
            verification_status=MechanicProfile.VerificationStatus.VERIFIED
        )

        # 2. Secondary Unverified Mechanic
        self.unverified_user = User.objects.create_user(
            username='tech_novice',
            email='novice@autovia.test',
            password=self.mechanic_password,
            first_name='Nate',
            last_name='Novice'
        )
        self.unverified_user_profile = self.unverified_user.profile
        self.unverified_user_profile.role = UserProfile.Role.MECHANIC
        self.unverified_user_profile.save()

        self.unverified_mechanic = MechanicProfile.objects.create(
            user=self.unverified_user,
            specialization='Oil Changes & Tyres',
            experience_years=1,
            service_location='East Suburbs',
            description='Junior mechanic pending verification.',
            is_available=True,
            verification_status=MechanicProfile.VerificationStatus.PENDING
        )

        # 3. Another Verified Mechanic (for duplicate acceptance test)
        self.mechanic2_user = User.objects.create_user(
            username='tech_brian',
            email='brian@autovia.test',
            password=self.mechanic_password,
            first_name='Brian',
            last_name='Torque'
        )
        self.mechanic2_user_profile = self.mechanic2_user.profile
        self.mechanic2_user_profile.role = UserProfile.Role.MECHANIC
        self.mechanic2_user_profile.save()

        self.mechanic2 = MechanicProfile.objects.create(
            user=self.mechanic2_user,
            specialization='Brakes & Suspension',
            experience_years=10,
            service_location='West Metro District',
            is_available=True,
            verification_status=MechanicProfile.VerificationStatus.VERIFIED
        )

        # 4. Vehicle Owner Customer
        self.owner_user = User.objects.create_user(
            username='driver_clara',
            email='clara@autovia.test',
            password=self.owner_password,
            first_name='Clara',
            last_name='Oswald'
        )
        self.owner_profile = self.owner_user.profile
        self.owner_profile.role = UserProfile.Role.VEHICLE_OWNER
        self.owner_profile.save()

        self.vehicle = Vehicle.objects.create(
            owner=self.owner_user,
            registration_number='TECH-777',
            manufacturer='Subaru',
            model_name='Forester',
            manufacturing_year=2021,
            fuel_type=Vehicle.FuelType.PETROL,
            color='Crystal Black',
            current_odometer=34000
        )

        # Default login as primary verified mechanic
        self.client.login(username='tech_alex', password=self.mechanic_password)

    # 1. Mechanic login and dashboard access
    def test_01_mechanic_login_and_dashboard_access(self):
        # Test access via accounts:mechanic_dashboard
        res_acct = self.client.get(reverse('accounts:mechanic_dashboard'))
        self.assertEqual(res_acct.status_code, 200)

        # Access dashboard directly
        response = self.client.get(reverse('mechanics:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alex')
        self.assertContains(response, 'Diagnostics &amp; Engine Repair')

        # Verify context metrics exist
        self.assertIn('total_incoming_requests', response.context)
        self.assertIn('accepted_count', response.context)
        self.assertIn('active_repairs_count', response.context)
        self.assertIn('completed_repairs_count', response.context)
        self.assertIn('total_earnings', response.context)

    # 2. Unverified mechanic restrictions
    def test_02_unverified_mechanic_restrictions(self):
        # Switch session to unverified mechanic
        self.client.login(username='tech_novice', password=self.mechanic_password)

        req = ServiceRequest.objects.create(
            vehicle=self.vehicle,
            customer=self.owner_user,
            problem_description='Strange whining noise from power steering pump',
            requested_date=timezone.now() + datetime.timedelta(days=1),
            status=ServiceRequest.Status.PENDING
        )

        # Attempt to accept request -> blocked
        res_accept = self.client.post(reverse('mechanics:accept_request', kwargs={'pk': req.pk}), follow=True)
        self.assertEqual(res_accept.status_code, 200)
        self.assertContains(res_accept, "pending admin verification")
        req.refresh_from_db()
        self.assertEqual(req.status, ServiceRequest.Status.PENDING)
        self.assertIsNone(req.mechanic)

        # Attempt to create estimate -> blocked
        res_est = self.client.get(reverse('mechanics:create_estimate', kwargs={'pk': req.pk}), follow=True)
        self.assertEqual(res_est.status_code, 200)
        self.assertContains(res_est, "Account verification required")

        # Attempt to generate bill -> blocked
        res_bill = self.client.get(reverse('mechanics:generate_bill', kwargs={'pk': req.pk}), follow=True)
        self.assertEqual(res_bill.status_code, 200)
        self.assertContains(res_bill, "Account verification required")

        # Profile view is still accessible
        res_prof = self.client.get(reverse('mechanics:profile'))
        self.assertEqual(res_prof.status_code, 200)

    # 3. Profile editing and verification protection
    def test_03_profile_editing_and_verification_protection(self):
        url = reverse('mechanics:profile')
        post_data = {
            'first_name': 'Alexander',
            'last_name': 'Vance',
            'phone_number': '+1-555-9988',
            'specialization': 'Advanced EV & Hybrid Powertrains',
            'experience_years': 9,
            'service_location': 'North Industrial Hub',
            'description': 'Master diagnostic technician with factory training.',
            'verification_status': 'REJECTED',  # Attempting to tamper
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.mechanic.refresh_from_db()
        self.mechanic_user.refresh_from_db()
        self.assertEqual(self.mechanic_user.first_name, 'Alexander')
        self.assertEqual(self.mechanic.specialization, 'Advanced EV & Hybrid Powertrains')
        self.assertEqual(self.mechanic.experience_years, 9)
        self.assertEqual(self.mechanic.service_location, 'North Industrial Hub')
        # Verification status remains VERIFIED (tampering blocked)
        self.assertEqual(self.mechanic.verification_status, MechanicProfile.VerificationStatus.VERIFIED)

    # 4. Availability updates
    def test_04_availability_updates(self):
        self.assertTrue(self.mechanic.is_available)

        # Toggle to unavailable
        res1 = self.client.post(reverse('mechanics:toggle_availability'), follow=True)
        self.assertEqual(res1.status_code, 200)
        self.mechanic.refresh_from_db()
        self.assertFalse(self.mechanic.is_available)

        # Toggle back to available
        res2 = self.client.post(reverse('mechanics:toggle_availability'), follow=True)
        self.assertEqual(res2.status_code, 200)
        self.mechanic.refresh_from_db()
        self.assertTrue(self.mechanic.is_available)

    # 5. Accepting service request
    def test_05_accepting_service_request(self):
        req = ServiceRequest.objects.create(
            vehicle=self.vehicle,
            customer=self.owner_user,
            problem_description='Check engine light code P0300 (Random Misfire)',
            requested_date=timezone.now() + datetime.timedelta(days=1),
            status=ServiceRequest.Status.PENDING
        )

        res = self.client.post(reverse('mechanics:accept_request', kwargs={'pk': req.pk}), follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertRedirects(res, reverse('mechanics:request_detail', kwargs={'pk': req.pk}))

        req.refresh_from_db()
        self.assertEqual(req.status, ServiceRequest.Status.ACCEPTED)
        self.assertEqual(req.mechanic, self.mechanic)

    # 6. Rejecting service request
    def test_06_rejecting_service_request(self):
        req = ServiceRequest.objects.create(
            vehicle=self.vehicle,
            customer=self.owner_user,
            mechanic=self.mechanic,
            problem_description='Bodywork dent repair needed',
            requested_date=timezone.now() + datetime.timedelta(days=1),
            status=ServiceRequest.Status.PENDING
        )

        res = self.client.post(reverse('mechanics:reject_request', kwargs={'pk': req.pk}), follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertRedirects(res, reverse('mechanics:incoming_requests'))

        req.refresh_from_db()
        self.assertEqual(req.status, ServiceRequest.Status.REJECTED)

    # 7. Duplicate request acceptance prevention
    def test_07_duplicate_request_acceptance(self):
        req = ServiceRequest.objects.create(
            vehicle=self.vehicle,
            customer=self.owner_user,
            problem_description='Brake fluid flush and ABS sensor check',
            requested_date=timezone.now() + datetime.timedelta(days=1),
            status=ServiceRequest.Status.PENDING
        )

        # First mechanic accepts
        res1 = self.client.post(reverse('mechanics:accept_request', kwargs={'pk': req.pk}))
        self.assertEqual(res1.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, ServiceRequest.Status.ACCEPTED)
        self.assertEqual(req.mechanic, self.mechanic)

        # Second mechanic attempts to accept the same ticket
        self.client.login(username='tech_brian', password=self.mechanic_password)
        res2 = self.client.post(reverse('mechanics:accept_request', kwargs={'pk': req.pk}), follow=True)
        self.assertEqual(res2.status_code, 200)
        self.assertContains(res2, "can no longer be accepted")

        req.refresh_from_db()
        # Still assigned to original mechanic
        self.assertEqual(req.mechanic, self.mechanic)

    # 8. Estimate generation
    def test_08_estimate_generation(self):
        req = ServiceRequest.objects.create(
            vehicle=self.vehicle,
            customer=self.owner_user,
            mechanic=self.mechanic,
            problem_description='Worn front brake rotors and pads',
            requested_date=timezone.now() + datetime.timedelta(days=1),
            status=ServiceRequest.Status.ACCEPTED
        )

        url = reverse('mechanics:create_estimate', kwargs={'pk': req.pk})
        estimate_data = {
            'labor_cost': '140.00',
            'parts_cost': '220.50',
            'additional_cost': '25.00',
            'estimated_completion_date': (datetime.date.today() + datetime.timedelta(days=3)).strftime('%Y-%m-%d'),
            'description': 'Replace front Brembo rotors and carbon-ceramic pads with fluid bleed.',
        }
        response = self.client.post(url, estimate_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('mechanics:request_detail', kwargs={'pk': req.pk}))

        estimate = RepairEstimate.objects.get(service_request=req, provider=self.mechanic_user)
        self.assertEqual(estimate.labor_cost, Decimal('140.00'))
        self.assertEqual(estimate.parts_cost, Decimal('220.50'))
        self.assertEqual(estimate.additional_cost, Decimal('25.00'))

    # 9. Estimate calculations
    def test_09_estimate_automatic_calculation(self):
        req = ServiceRequest.objects.create(
            vehicle=self.vehicle,
            customer=self.owner_user,
            mechanic=self.mechanic,
            problem_description='Clutch slipping under acceleration',
            requested_date=timezone.now() + datetime.timedelta(days=1),
            status=ServiceRequest.Status.ACCEPTED
        )

        estimate = RepairEstimate.objects.create(
            service_request=req,
            provider=self.mechanic_user,
            labor_cost=Decimal('250.00'),
            parts_cost=Decimal('450.00'),
            additional_cost=Decimal('50.00'),
            description='Stage 2 clutch kit and flywheel resurfacing'
        )
        # Verify automatic total calculation on save
        self.assertEqual(estimate.total_cost, Decimal('750.00'))

        # Update parts cost
        estimate.parts_cost = Decimal('500.00')
        estimate.save()
        estimate.refresh_from_db()
        self.assertEqual(estimate.total_cost, Decimal('800.00'))

    # 10. Repair progress updates
    def test_10_repair_progress_milestone_updates(self):
        req = ServiceRequest.objects.create(
            vehicle=self.vehicle,
            customer=self.owner_user,
            mechanic=self.mechanic,
            problem_description='Transmission fluid leak at pan gasket',
            requested_date=timezone.now() + datetime.timedelta(days=1),
            status=ServiceRequest.Status.ACCEPTED
        )

        update_url = reverse('mechanics:update_repair_status', kwargs={'pk': req.pk})

        # Valid transition: ACCEPTED -> IN_PROGRESS
        res1 = self.client.post(update_url, {'status': 'IN_PROGRESS'}, follow=True)
        self.assertEqual(res1.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.status, ServiceRequest.Status.IN_PROGRESS)

        # Invalid transition: IN_PROGRESS -> ACCEPTED (backwards transition blocked)
        res_invalid = self.client.post(update_url, {'status': 'ACCEPTED'}, follow=True)
        self.assertEqual(res_invalid.status_code, 200)
        self.assertContains(res_invalid, "Invalid status transition")
        req.refresh_from_db()
        self.assertEqual(req.status, ServiceRequest.Status.IN_PROGRESS)

        # Valid transition: IN_PROGRESS -> COMPLETED
        res2 = self.client.post(update_url, {'status': 'COMPLETED'}, follow=True)
        self.assertEqual(res2.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.status, ServiceRequest.Status.COMPLETED)

    # 11. Bill generation and service record synchronization
    def test_11_bill_generation_and_service_record_sync(self):
        req = ServiceRequest.objects.create(
            vehicle=self.vehicle,
            customer=self.owner_user,
            mechanic=self.mechanic,
            problem_description='Routine 30k interval full service',
            requested_date=timezone.now() + datetime.timedelta(days=1),
            status=ServiceRequest.Status.IN_PROGRESS
        )

        url = reverse('mechanics:generate_bill', kwargs={'pk': req.pk})
        bill_data = {
            'service_description': 'Replaced engine oil with 5W-30 synthetic, OEM oil filter, new engine air filter, and tire rotation.',
            'labor_charges': '125.00',
            'parts_charges': '95.50',
            'additional_charges': '15.00',
            'service_date': datetime.date.today().strftime('%Y-%m-%d'),
            'payment_method': RepairBill.PaymentMethod.CARD,
            'is_paid': True,
        }

        res = self.client.post(url, bill_data, follow=True)
        self.assertEqual(res.status_code, 200)

        # Confirm RepairBill in DB
        bill = RepairBill.objects.get(service_request=req)
        self.assertEqual(bill.total_amount, Decimal('235.50'))
        self.assertTrue(bill.is_paid)

        # Confirm ServiceRequest is COMPLETED
        req.refresh_from_db()
        self.assertEqual(req.status, ServiceRequest.Status.COMPLETED)

        # Confirm ServiceRecord is synchronized into owner's history log
        record = ServiceRecord.objects.get(service_request=req)
        self.assertEqual(record.vehicle, self.vehicle)
        self.assertEqual(record.total_cost, Decimal('235.50'))
        self.assertEqual(record.odometer_reading, self.vehicle.current_odometer)

        # Check mechanic dashboard earnings now aggregates this bill
        res_dash = self.client.get(reverse('mechanics:dashboard'))
        self.assertEqual(res_dash.context['total_earnings'], Decimal('235.50'))

    # 12. Unauthorized access and RBAC protection
    def test_12_unauthorized_access_and_rbac(self):
        # 1. Vehicle Owner attempting to access Mechanic pages -> 403 Forbidden
        self.client.login(username='driver_clara', password=self.owner_password)

        mechanic_urls = [
            reverse('mechanics:dashboard'),
            reverse('mechanics:profile'),
            reverse('mechanics:availability'),
            reverse('mechanics:incoming_requests'),
            reverse('mechanics:active_repairs'),
            reverse('mechanics:estimate_list'),
            reverse('mechanics:bill_list'),
            reverse('mechanics:feedback_list'),
        ]

        for u in mechanic_urls:
            res = self.client.get(u)
            self.assertEqual(res.status_code, 403, f"URL {u} did not block vehicle owner with 403")

        # 2. Anonymous user accessing mechanic pages -> redirected to login
        self.client.logout()
        for u in mechanic_urls:
            res_anon = self.client.get(u)
            self.assertEqual(res_anon.status_code, 302)
            self.assertIn(reverse('accounts:login'), res_anon.url)
