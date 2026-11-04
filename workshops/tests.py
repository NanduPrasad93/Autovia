from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
import datetime

from accounts.models import UserProfile
from workshops.models import Workshop
from vehicles.models import Vehicle
from services.models import ServiceRequest, RepairEstimate, ServiceRecord, RepairBill, ServiceFeedback


class WorkshopDashboardTests(TestCase):
    """
    Comprehensive test suite for STEP 9: Workshop / Service Centre Dashboard.
    Covers RBAC, verification gating, incoming requests, atomic concurrency,
    estimates, bay repair hoist, invoicing, history sync, feedback, and analytics.
    """

    def setUp(self):
        self.client = Client()

        # 1. Workshop Owner A
        self.workshop_user = User.objects.create_user(
            username='apex_workshop',
            email='apex@workshop.com',
            password='Workshop@Pass123!',
            first_name='Apex',
            last_name='Motors'
        )
        self.workshop_profile, _ = UserProfile.objects.get_or_create(
            user=self.workshop_user,
            defaults={'role': UserProfile.Role.WORKSHOP, 'phone_number': '+1-555-019-1001'}
        )
        self.workshop_profile.role = UserProfile.Role.WORKSHOP
        self.workshop_profile.save()

        self.workshop = Workshop.objects.create(
            owner=self.workshop_user,
            workshop_name='Apex Auto Care & Service Centre',
            description='Full-service automotive diagnostic and mechanical workshop facility.',
            address='100 Industrial Parkway, Sector 4',
            phone_number='+1-555-019-1001',
            services_offered='Engine Diagnostics, Transmission Repair, Brake System Overhaul',
            verification_status=Workshop.VerificationStatus.PENDING
        )

        # 2. Workshop Owner B (for IDOR testing)
        self.workshop_user_b = User.objects.create_user(
            username='metro_garage',
            email='metro@garage.com',
            password='WorkshopB@Pass123!',
            first_name='Metro',
            last_name='Garage'
        )
        self.workshop_profile_b, _ = UserProfile.objects.get_or_create(
            user=self.workshop_user_b,
            defaults={'role': UserProfile.Role.WORKSHOP, 'phone_number': '+1-555-019-2002'}
        )
        self.workshop_profile_b.role = UserProfile.Role.WORKSHOP
        self.workshop_profile_b.save()

        self.workshop_b = Workshop.objects.create(
            owner=self.workshop_user_b,
            workshop_name='Metro Speed Garage',
            description='Specialized body work and suspension center.',
            address='202 Commercial Blvd',
            phone_number='+1-555-019-2002',
            services_offered='Body Work, Wheel Alignment, Paint',
            verification_status=Workshop.VerificationStatus.APPROVED
        )

        # 3. Vehicle Owner (Customer)
        self.customer = User.objects.create_user(
            username='car_owner_dan',
            email='dan@example.com',
            password='Owner@Pass123!',
            first_name='Dan',
            last_name='Miller'
        )
        self.customer_profile, _ = UserProfile.objects.get_or_create(user=self.customer)
        self.customer_profile.role = UserProfile.Role.VEHICLE_OWNER
        self.customer_profile.phone_number = '+1-555-019-3003'
        self.customer_profile.save()

        self.vehicle = Vehicle.objects.create(
            owner=self.customer,
            registration_number='WS-9988-TX',
            manufacturer='Toyota',
            model_name='RAV4 Hybrid',
            manufacturing_year=2023,
            fuel_type=Vehicle.FuelType.HYBRID,
            color='Silver Metallic',
            current_odometer=18500
        )

        # 4. Service Request
        from django.utils import timezone
        self.service_request = ServiceRequest.objects.create(
            vehicle=self.vehicle,
            customer=self.customer,
            workshop=self.workshop,
            problem_description='Hybrid inverter fault code and front suspension rattle at 60 km/h.',
            requested_date=timezone.now() + datetime.timedelta(days=2),
            status=ServiceRequest.Status.PENDING
        )

    # -------------------------------------------------------------
    # 1. Login & Dashboard Access
    # -------------------------------------------------------------
    def test_01_workshop_login_and_dashboard_access(self):
        """Test workshop user login and accessing both dashboard endpoints."""
        login_success = self.client.login(username='apex_workshop', password='Workshop@Pass123!')
        self.assertTrue(login_success)

        # Access direct workshop route
        res = self.client.get(reverse('workshops:dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Apex Auto Care &amp; Service Centre')
        self.assertContains(res, 'Total Requests')
        self.assertContains(res, 'In Service Bay')

        # Access accounts alias route
        res_alias = self.client.get(reverse('accounts:workshop_dashboard'))
        self.assertEqual(res_alias.status_code, 200)
        self.assertContains(res_alias, 'Apex Auto Care &amp; Service Centre')

    # -------------------------------------------------------------
    # 2. Workshop Profile View & Editing
    # -------------------------------------------------------------
    def test_02_workshop_profile_editing_and_verification_protection(self):
        """Test editing workshop profile and ensuring verification status cannot be self-modified."""
        self.client.login(username='apex_workshop', password='Workshop@Pass123!')

        # Verify initial profile view
        res = self.client.get(reverse('workshops:profile'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Apex Auto Care &amp; Service Centre')

        # Update workshop profile fields and attempt privilege escalation
        post_data = {
            'workshop_name': 'Apex Precision Auto Centre',
            'description': 'Updated modern multi-bay automotive service hub.',
            'address': '500 Technology Drive, Suite 10',
            'phone_number': '+1-555-019-9999',
            'services_offered': 'Advanced EV diagnostics, Hybrid powertrain, Laser wheel alignment',
            # Malicious attempt to self-verify
            'verification_status': 'APPROVED',
        }
        res_post = self.client.post(reverse('workshops:profile'), data=post_data, follow=True)
        self.assertEqual(res_post.status_code, 200)

        self.workshop.refresh_from_db()
        self.assertEqual(self.workshop.workshop_name, 'Apex Precision Auto Centre')
        self.assertEqual(self.workshop.phone_number, '+1-555-019-9999')
        # Verification status MUST remain PENDING
        self.assertEqual(self.workshop.verification_status, Workshop.VerificationStatus.PENDING)
        self.assertFalse(self.workshop.is_approved)

    # -------------------------------------------------------------
    # 3. Pending Verification Restrictions
    # -------------------------------------------------------------
    def test_03_pending_verification_restrictions(self):
        """Test that unapproved/pending workshops are blocked from accepting tickets, estimating, or billing."""
        self.client.login(username='apex_workshop', password='Workshop@Pass123!')
        self.assertEqual(self.workshop.verification_status, Workshop.VerificationStatus.PENDING)

        # 1. Attempt to accept service ticket
        res_accept = self.client.post(reverse('workshops:accept_request', kwargs={'pk': self.service_request.pk}), follow=True)
        self.assertContains(res_accept, 'Only verified and approved workshops are authorized')
        self.service_request.refresh_from_db()
        self.assertEqual(self.service_request.status, ServiceRequest.Status.PENDING)

        # 2. Attempt to create estimate
        res_est = self.client.get(reverse('workshops:create_estimate', kwargs={'pk': self.service_request.pk}), follow=True)
        self.assertContains(res_est, 'Your workshop facility must be approved before you can submit official repair estimates')

        # 3. Attempt to generate bill
        res_bill = self.client.get(reverse('workshops:generate_bill', kwargs={'pk': self.service_request.pk}), follow=True)
        self.assertContains(res_bill, 'Workshop approval is required to issue official repair bills')

    # -------------------------------------------------------------
    # 4. Approved Workshop Access
    # -------------------------------------------------------------
    def test_04_approved_workshop_access(self):
        """Test that approved workshops can access verification screen and full operations."""
        self.workshop.verification_status = Workshop.VerificationStatus.APPROVED
        self.workshop.save()
        self.assertTrue(self.workshop.is_approved)

        self.client.login(username='apex_workshop', password='Workshop@Pass123!')

        res = self.client.get(reverse('workshops:verification_status'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'APPROVED')
        self.assertContains(res, 'authorized to accept incoming service requests')

    # -------------------------------------------------------------
    # 5. Incoming Requests & Details
    # -------------------------------------------------------------
    def test_05_view_incoming_requests_and_details(self):
        """Test viewing incoming requests list and ticket inspection."""
        self.client.login(username='apex_workshop', password='Workshop@Pass123!')

        # Create an unassigned open request as well
        from django.utils import timezone
        open_req = ServiceRequest.objects.create(
            vehicle=self.vehicle,
            customer=self.customer,
            problem_description='Routine 20k km oil and filter change.',
            requested_date=timezone.now() + datetime.timedelta(days=3),
            status=ServiceRequest.Status.PENDING
        )

        # Create a request assigned exclusively to another workshop
        other_req = ServiceRequest.objects.create(
            vehicle=self.vehicle,
            customer=self.customer,
            workshop=self.workshop_b,
            problem_description='Exclusive request for workshop B.',
            requested_date=timezone.now() + datetime.timedelta(days=1),
            status=ServiceRequest.Status.PENDING
        )

        res = self.client.get(reverse('workshops:incoming_requests'))
        self.assertEqual(res.status_code, 200)
        # Targeted request and open unassigned request must appear
        self.assertContains(res, 'WS-9988-TX')
        self.assertContains(res, 'Hybrid inverter fault code')
        self.assertContains(res, 'Routine 20k km oil and filter change')
        # Private request for workshop B must NOT appear
        self.assertNotContains(res, 'Exclusive request for workshop B')

        # Request detail inspection
        res_detail = self.client.get(reverse('workshops:request_detail', kwargs={'pk': self.service_request.pk}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, 'Toyota RAV4 Hybrid')
        self.assertContains(res_detail, 'Dan Miller')
        self.assertContains(res_detail, '+1-555-019-3003')

    # -------------------------------------------------------------
    # 6. Concurrency-Safe Request Acceptance
    # -------------------------------------------------------------
    def test_06_accept_service_request_and_duplicate_prevention(self):
        """Test atomic acceptance of a service request and prevention of duplicate claims."""
        self.workshop.verification_status = Workshop.VerificationStatus.APPROVED
        self.workshop.save()

        self.client.login(username='apex_workshop', password='Workshop@Pass123!')

        # Accept request
        res = self.client.post(reverse('workshops:accept_request', kwargs={'pk': self.service_request.pk}), follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, f"Service Request #{self.service_request.pk} has been accepted!")

        self.service_request.refresh_from_db()
        self.assertEqual(self.service_request.status, ServiceRequest.Status.ACCEPTED)
        self.assertEqual(self.service_request.workshop, self.workshop)

        # Another workshop attempts to claim the already-accepted request
        self.client.logout()
        self.client.login(username='metro_garage', password='WorkshopB@Pass123!')

        res_double = self.client.post(reverse('workshops:accept_request', kwargs={'pk': self.service_request.pk}), follow=True)
        self.assertContains(res_double, "This request has already been assigned to another workshop")

    # -------------------------------------------------------------
    # 7. Reject Request
    # -------------------------------------------------------------
    def test_07_reject_service_request(self):
        """Test rejecting an incoming service request."""
        self.client.login(username='apex_workshop', password='Workshop@Pass123!')

        res = self.client.post(reverse('workshops:reject_request', kwargs={'pk': self.service_request.pk}), follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, f"Service Request #{self.service_request.pk} has been rejected")

        self.service_request.refresh_from_db()
        self.assertEqual(self.service_request.status, ServiceRequest.Status.REJECTED)

    # -------------------------------------------------------------
    # 8. Repair Estimate Calculations & Editing
    # -------------------------------------------------------------
    def test_08_repair_estimate_calculations(self):
        """Test preparing quotation, verifying auto-calculation of total, and editing."""
        self.workshop.verification_status = Workshop.VerificationStatus.APPROVED
        self.workshop.save()
        self.service_request.status = ServiceRequest.Status.ACCEPTED
        self.service_request.save()

        self.client.login(username='apex_workshop', password='Workshop@Pass123!')

        post_data = {
            'labor_cost': '350.00',
            'parts_cost': '600.00',
            'additional_cost': '50.00',
            'estimated_completion_date': (datetime.date.today() + datetime.timedelta(days=4)).strftime('%Y-%m-%d'),
            'description': 'Replace hybrid cooling pump and flush inverter fluid.',
        }
        res = self.client.post(reverse('workshops:create_estimate', kwargs={'pk': self.service_request.pk}), data=post_data, follow=True)
        self.assertEqual(res.status_code, 200)

        estimate = RepairEstimate.objects.get(service_request=self.service_request, provider=self.workshop_user)
        self.assertEqual(estimate.labor_cost, Decimal('350.00'))
        self.assertEqual(estimate.parts_cost, Decimal('600.00'))
        self.assertEqual(estimate.additional_cost, Decimal('50.00'))
        # Total cost MUST auto-calculate to 350 + 600 + 50 = 1000.00
        self.assertEqual(estimate.total_cost, Decimal('1000.00'))

        # Edit estimate
        edit_data = {
            'labor_cost': '400.00',
            'parts_cost': '550.00',
            'additional_cost': '0.00',
            'estimated_completion_date': (datetime.date.today() + datetime.timedelta(days=3)).strftime('%Y-%m-%d'),
            'description': 'Updated: OEM pump supplied with discounted labor.',
        }
        res_edit = self.client.post(reverse('workshops:edit_estimate', kwargs={'pk': self.service_request.pk}), data=edit_data, follow=True)
        self.assertEqual(res_edit.status_code, 200)

        estimate.refresh_from_db()
        self.assertEqual(estimate.total_cost, Decimal('950.00'))

    # -------------------------------------------------------------
    # 9. Repair Progress Updates
    # -------------------------------------------------------------
    def test_09_repair_progress_updates(self):
        """Test progressing repair status: ACCEPTED -> IN_PROGRESS."""
        self.workshop.verification_status = Workshop.VerificationStatus.APPROVED
        self.workshop.save()
        self.service_request.status = ServiceRequest.Status.ACCEPTED
        self.service_request.save()

        self.client.login(username='apex_workshop', password='Workshop@Pass123!')

        # Transition to IN_PROGRESS
        res = self.client.post(
            reverse('workshops:update_repair_status', kwargs={'pk': self.service_request.pk}),
            data={'status': 'IN_PROGRESS'},
            follow=True
        )
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'In Progress')

        self.service_request.refresh_from_db()
        self.assertEqual(self.service_request.status, ServiceRequest.Status.IN_PROGRESS)

        # Invalid backwards transition should be rejected
        res_invalid = self.client.post(
            reverse('workshops:update_repair_status', kwargs={'pk': self.service_request.pk}),
            data={'status': 'PENDING'},
            follow=True
        )
        self.assertContains(res_invalid, 'Invalid status transition')

    # -------------------------------------------------------------
    # 10. Generate Bill & Service Record Synchronization
    # -------------------------------------------------------------
    def test_10_generate_repair_bill_and_service_history_sync(self):
        """Test issuing official repair bill, completing request, and syncing ServiceRecord."""
        self.workshop.verification_status = Workshop.VerificationStatus.APPROVED
        self.workshop.save()
        self.service_request.status = ServiceRequest.Status.IN_PROGRESS
        self.service_request.save()

        self.client.login(username='apex_workshop', password='Workshop@Pass123!')

        bill_data = {
            'service_description': 'Installed OEM hybrid inverter pump, flushed coolant, and performed road test.',
            'labor_charges': '300.00',
            'parts_charges': '550.00',
            'additional_charges': '45.00',
            'service_date': datetime.date.today().strftime('%Y-%m-%d'),
            'payment_method': 'CARD',
            'is_paid': True,
        }
        res = self.client.post(reverse('workshops:generate_bill', kwargs={'pk': self.service_request.pk}), data=bill_data, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Official Repair Bill')

        # Verify bill amounts
        bill = RepairBill.objects.get(service_request=self.service_request)
        self.assertEqual(bill.total_amount, Decimal('895.00'))
        self.assertTrue(bill.is_paid)

        # ServiceRequest must be COMPLETED
        self.service_request.refresh_from_db()
        self.assertEqual(self.service_request.status, ServiceRequest.Status.COMPLETED)

        # ServiceRecord must be created and linked to vehicle
        record = ServiceRecord.objects.get(service_request=self.service_request)
        self.assertEqual(record.vehicle, self.vehicle)
        self.assertEqual(record.total_cost, Decimal('895.00'))
        self.assertEqual(record.odometer_reading, self.vehicle.current_odometer)

    # -------------------------------------------------------------
    # 11. Customer Feedback & Review Display
    # -------------------------------------------------------------
    def test_11_customer_feedback_display(self):
        """Test customer submitting feedback and workshop viewing reviews."""
        self.service_request.status = ServiceRequest.Status.COMPLETED
        self.service_request.save()

        # Customer submits feedback
        feedback = ServiceFeedback.objects.create(
            service_request=self.service_request,
            customer=self.customer,
            workshop=self.workshop,
            rating=5,
            comment='Outstanding technical expertise! Hybrid inverter issue resolved on time.'
        )

        self.client.login(username='apex_workshop', password='Workshop@Pass123!')
        res = self.client.get(reverse('workshops:feedback'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Outstanding technical expertise')
        self.assertContains(res, '5.0')
        self.assertEqual(self.workshop.get_average_rating(), 5.0)

    # -------------------------------------------------------------
    # 12. Workshop Data Isolation & IDOR Protection
    # -------------------------------------------------------------
    def test_12_workshop_data_isolation_and_idor(self):
        """Test that Workshop B cannot modify Workshop A's private estimates or requests."""
        self.workshop.verification_status = Workshop.VerificationStatus.APPROVED
        self.workshop.save()
        self.service_request.status = ServiceRequest.Status.ACCEPTED
        self.service_request.save()

        # Workshop A creates estimate
        estimate_a = RepairEstimate.objects.create(
            service_request=self.service_request,
            provider=self.workshop_user,
            labor_cost=Decimal('200.00'),
            parts_cost=Decimal('100.00'),
            additional_cost=Decimal('0.00')
        )

        # Login as Workshop B
        self.client.login(username='metro_garage', password='WorkshopB@Pass123!')

        # Attempt to edit Workshop A's estimate for Request A
        res_idor = self.client.get(reverse('workshops:create_estimate', kwargs={'pk': self.service_request.pk}))
        # Request belongs to Workshop A, so Workshop B gets 404
        self.assertEqual(res_idor.status_code, 404)

        # Attempt to progress Workshop A's repair
        res_tamper = self.client.post(
            reverse('workshops:update_repair_status', kwargs={'pk': self.service_request.pk}),
            data={'status': 'IN_PROGRESS'}
        )
        self.assertEqual(res_tamper.status_code, 404)

    # -------------------------------------------------------------
    # 13. Unauthorized Access & RBAC Protection
    # -------------------------------------------------------------
    def test_13_unauthorized_access_and_rbac(self):
        """Test that non-workshop roles receive HTTP 403 Forbidden when accessing workshop portal."""
        # Vehicle owner login
        self.client.login(username='car_owner_dan', password='Owner@Pass123!')
        res_owner = self.client.get(reverse('workshops:dashboard'))
        self.assertEqual(res_owner.status_code, 403)

        res_owner_incoming = self.client.get(reverse('workshops:incoming_requests'))
        self.assertEqual(res_owner_incoming.status_code, 403)

        # Unauthenticated user
        self.client.logout()
        res_anon = self.client.get(reverse('workshops:dashboard'))
        self.assertEqual(res_anon.status_code, 302)
        self.assertIn('/accounts/login/', res_anon.url)

    # -------------------------------------------------------------
    # 14. Business Analytics & Statistics
    # -------------------------------------------------------------
    def test_14_business_analytics_and_statistics(self):
        """Test business analytics calculations and rendering."""
        self.workshop.verification_status = Workshop.VerificationStatus.APPROVED
        self.workshop.save()
        self.service_request.status = ServiceRequest.Status.COMPLETED
        self.service_request.save()

        RepairBill.objects.create(
            service_request=self.service_request,
            provider=self.workshop_user,
            customer=self.customer,
            vehicle=self.vehicle,
            service_description='Comprehensive overhaul',
            labor_charges=Decimal('500.00'),
            parts_charges=Decimal('500.00'),
            additional_charges=Decimal('0.00'),
            is_paid=True
        )

        self.client.login(username='apex_workshop', password='Workshop@Pass123!')
        res = self.client.get(reverse('workshops:analytics'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Business Analytics & Performance')
        self.assertContains(res, '1000.00')
        self.assertContains(res, 'Completion Efficiency Rate')
