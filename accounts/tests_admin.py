from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from decimal import Decimal

from accounts.models import UserProfile, Complaint, ActivityLog
from mechanics.models import MechanicProfile
from workshops.models import Workshop
from suppliers.models import SupplierProfile, SparePart
from vehicles.models import Vehicle
from services.models import ServiceRequest, RepairEstimate, RepairBill, ServiceFeedback


class AdminDashboardComprehensiveTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'AutoVia@SecTest2026!'

        # 1. Superuser
        self.superuser = User.objects.create_superuser(
            username='admin_super',
            email='super@autovia.test',
            password=self.password,
            first_name='Super',
            last_name='Admin'
        )
        self.superuser_profile = self.superuser.profile
        self.superuser_profile.role = UserProfile.Role.ADMIN
        self.superuser_profile.phone_number = '1112223333'
        self.superuser_profile.save()

        # 2. Staff user (Staff but not Superuser)
        self.staff_user = User.objects.create_user(
            username='admin_staff',
            email='staff@autovia.test',
            password=self.password,
            first_name='Staff',
            last_name='Officer',
            is_staff=True,
            is_superuser=False
        )
        self.staff_profile = self.staff_user.profile
        self.staff_profile.role = UserProfile.Role.ADMIN
        self.staff_profile.phone_number = '2223334444'
        self.staff_profile.save()

        # 3. Rogue/Non-Staff user with Role.ADMIN in profile but is_staff=False, is_superuser=False
        self.fake_admin = User.objects.create_user(
            username='fake_admin',
            email='fake@autovia.test',
            password=self.password,
            is_staff=False,
            is_superuser=False
        )
        self.fake_admin_profile = self.fake_admin.profile
        self.fake_admin_profile.role = UserProfile.Role.ADMIN
        self.fake_admin_profile.save()

        # 4. Vehicle Owner
        self.owner_user = User.objects.create_user(
            username='customer_bob',
            email='bob@autovia.test',
            password=self.password,
            first_name='Bob',
            last_name='Taylor'
        )
        self.owner_profile = self.owner_user.profile
        self.owner_profile.role = UserProfile.Role.VEHICLE_OWNER
        self.owner_profile.phone_number = '3334445555'
        self.owner_profile.save()

        # 5. Mechanic User & Profile (Pending initially)
        self.mechanic_user = User.objects.create_user(
            username='mechanic_dave',
            email='dave@autovia.test',
            password=self.password,
            first_name='Dave',
            last_name='Mechanic'
        )
        self.mechanic_user_profile = self.mechanic_user.profile
        self.mechanic_user_profile.role = UserProfile.Role.MECHANIC
        self.mechanic_user_profile.save()
        self.mechanic_profile = MechanicProfile.objects.create(
            user=self.mechanic_user,
            specialization='Transmission Systems',
            service_location='North Sector',
            experience_years=6,
            verification_status=MechanicProfile.VerificationStatus.PENDING
        )

        # 6. Workshop User & Profile (Pending initially)
        self.workshop_user = User.objects.create_user(
            username='workshop_tom',
            email='tom@autovia.test',
            password=self.password,
            first_name='Tom',
            last_name='Workshop'
        )
        self.workshop_user_profile = self.workshop_user.profile
        self.workshop_user_profile.role = UserProfile.Role.WORKSHOP
        self.workshop_user_profile.save()
        self.workshop = Workshop.objects.create(
            owner=self.workshop_user,
            workshop_name='Apex Performance Garage',
            address='100 Industrial Ave',
            phone_number='4445556666',
            verification_status=Workshop.VerificationStatus.PENDING
        )

        # 7. Supplier User & Profile (Pending initially)
        self.supplier_user = User.objects.create_user(
            username='supplier_sam',
            email='sam@autovia.test',
            password=self.password,
            first_name='Sam',
            last_name='Supplier'
        )
        self.supplier_user_profile = self.supplier_user.profile
        self.supplier_user_profile.role = UserProfile.Role.SUPPLIER
        self.supplier_user_profile.save()
        self.supplier_profile = SupplierProfile.objects.create(
            user=self.supplier_user,
            business_name='Apex Auto Parts Depot',
            business_address='50 Industrial Way',
            phone_number='5556667777',
            verification_status=SupplierProfile.VerificationStatus.PENDING
        )

        # 8. Vehicle & Service Request for monitoring tests
        self.vehicle = Vehicle.objects.create(
            owner=self.owner_user,
            manufacturer='Toyota',
            model_name='Camry',
            manufacturing_year=2021,
            registration_number='TEST-REG-101',
            fuel_type='PETROL',
            color='Silver',
            current_odometer=35000
        )

        self.service_request = ServiceRequest.objects.create(
            vehicle=self.vehicle,
            customer=self.owner_user,
            mechanic=self.mechanic_profile,
            problem_description='Strange grinding noise during heavy braking on highway.',
            requested_date=timezone.now() + datetime.timedelta(days=2),
            status=ServiceRequest.Status.PENDING
        )

    # 1. Admin dashboard access for Staff and Superusers
    def test_01_admin_dashboard_access_staff_and_superuser(self):
        # Superuser access
        self.client.login(username='admin_super', password=self.password)
        res_super = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(res_super.status_code, 200)
        self.assertContains(res_super, "AutoVia Administration")
        self.assertIn('total_users', res_super.context)
        self.assertIn('pending_mechanic_verifications', res_super.context)
        self.assertIn('pending_workshop_approvals', res_super.context)
        self.assertIn('pending_supplier_verifications', res_super.context)
        self.assertIn('total_pending_verifications', res_super.context)
        self.assertGreaterEqual(res_super.context['total_users'], 5)
        self.client.logout()

        # Staff user access
        self.client.login(username='admin_staff', password=self.password)
        res_staff = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(res_staff.status_code, 200)
        self.assertContains(res_staff, "Staff Officer")
        self.client.logout()

    # 2. Admin access strictly rejected for non-staff roles (HTTP 403)
    def test_02_admin_access_rejected_for_non_staff(self):
        # Vehicle Owner
        self.client.login(username='customer_bob', password=self.password)
        res_owner = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(res_owner.status_code, 403)
        self.client.logout()

        # Mechanic
        self.client.login(username='mechanic_dave', password=self.password)
        res_mech = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(res_mech.status_code, 403)
        self.client.logout()

        # Workshop
        self.client.login(username='workshop_tom', password=self.password)
        res_ws = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(res_ws.status_code, 403)
        self.client.logout()

        # Supplier
        self.client.login(username='supplier_sam', password=self.password)
        res_sup = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(res_sup.status_code, 403)
        self.client.logout()

        # Role=ADMIN in profile but NOT is_staff or is_superuser
        self.client.login(username='fake_admin', password=self.password)
        res_fake = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(res_fake.status_code, 403)
        self.client.logout()

    # 3. Unauthenticated access redirected to login
    def test_03_unauthenticated_redirect_to_login(self):
        res = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('accounts:login'), res.url)
        self.assertIn('next=/admin-dashboard/', res.url)

    # 4. User listing, search, and role filtering
    def test_04_user_listing_search_and_role_filtering(self):
        self.client.login(username='admin_staff', password=self.password)

        # Baseline list
        res_all = self.client.get(reverse('admin_dashboard:users'))
        self.assertEqual(res_all.status_code, 200)
        self.assertContains(res_all, "customer_bob")
        self.assertContains(res_all, "mechanic_dave")

        # Search filter
        res_search = self.client.get(reverse('admin_dashboard:users'), {'q': 'bob'})
        self.assertEqual(res_search.status_code, 200)
        self.assertContains(res_search, "customer_bob")
        self.assertNotContains(res_search, "mechanic_dave")

        # Role filter
        res_role = self.client.get(reverse('admin_dashboard:users'), {'role': UserProfile.Role.MECHANIC})
        self.assertEqual(res_role.status_code, 200)
        self.assertContains(res_role, "mechanic_dave")
        self.assertNotContains(res_role, "customer_bob")

        # Status filter
        res_active = self.client.get(reverse('admin_dashboard:users'), {'status': '1'})
        self.assertEqual(res_active.status_code, 200)
        self.assertContains(res_active, "customer_bob")

    # 5. User activation and deactivation
    def test_05_user_activation_and_deactivation(self):
        self.client.login(username='admin_staff', password=self.password)
        self.assertTrue(self.owner_user.is_active)

        # Deactivate user
        res_deact = self.client.post(
            reverse('admin_dashboard:user_toggle_status', kwargs={'pk': self.owner_user.pk}),
            follow=True
        )
        self.assertEqual(res_deact.status_code, 200)
        self.owner_user.refresh_from_db()
        self.assertFalse(self.owner_user.is_active)

        # Check ActivityLog recorded
        log = ActivityLog.objects.filter(
            action_type=ActivityLog.ActionType.USER_STATUS,
            target_object_id=str(self.owner_user.pk)
        ).first()
        self.assertIsNotNone(log)
        self.assertIn("deactivated", log.description)
        self.assertEqual(log.user, self.staff_user)

        # Reactivate user
        res_act = self.client.post(
            reverse('admin_dashboard:user_toggle_status', kwargs={'pk': self.owner_user.pk}),
            follow=True
        )
        self.assertEqual(res_act.status_code, 200)
        self.owner_user.refresh_from_db()
        self.assertTrue(self.owner_user.is_active)

    # 6. Prevent administrator self-deactivation
    def test_06_prevent_admin_self_deactivation(self):
        self.client.login(username='admin_staff', password=self.password)

        res = self.client.post(
            reverse('admin_dashboard:user_toggle_status', kwargs={'pk': self.staff_user.pk}),
            follow=True
        )
        self.assertEqual(res.status_code, 200)
        self.staff_user.refresh_from_db()
        self.assertTrue(self.staff_user.is_active)
        self.assertContains(res, "Administrators cannot deactivate their own active user account")

    # 7. Protect superuser account from staff deactivation
    def test_07_protect_superuser_from_staff_deactivation(self):
        # Staff user attempting to deactivate Superuser
        self.client.login(username='admin_staff', password=self.password)

        res = self.client.post(
            reverse('admin_dashboard:user_toggle_status', kwargs={'pk': self.superuser.pk}),
            follow=True
        )
        self.assertEqual(res.status_code, 200)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)
        self.assertContains(res, "Only superusers can modify another superuser account")

    # 8. Mechanic verification: Approve and Reject
    def test_08_mechanic_verification_approve_and_reject(self):
        self.client.login(username='admin_staff', password=self.password)

        # 8a. Approve mechanic
        res_approve = self.client.post(
            reverse('admin_dashboard:mechanic_detail', kwargs={'pk': self.mechanic_profile.pk}),
            {'action': 'approve'},
            follow=True
        )
        self.assertEqual(res_approve.status_code, 200)
        self.mechanic_profile.refresh_from_db()
        self.assertEqual(self.mechanic_profile.verification_status, MechanicProfile.VerificationStatus.VERIFIED)
        self.assertTrue(self.mechanic_profile.is_verified)
        self.assertEqual(self.mechanic_profile.rejection_reason, '')

        # Check activity log
        log = ActivityLog.objects.filter(
            action_type=ActivityLog.ActionType.MECHANIC_VERIFICATION,
            target_object_id=str(self.mechanic_profile.pk)
        ).first()
        self.assertIsNotNone(log)
        self.assertIn("Approved mechanic application", log.description)

        # 8b. Create second mechanic and reject with reason
        mech_reject_user = User.objects.create_user(
            username='mechanic_reject',
            email='reject@autovia.test',
            password=self.password
        )
        mech_reject_profile = MechanicProfile.objects.create(
            user=mech_reject_user,
            specialization='General',
            verification_status=MechanicProfile.VerificationStatus.PENDING
        )

        reason = "Trade certifications unverified and background check pending."
        res_reject = self.client.post(
            reverse('admin_dashboard:mechanic_detail', kwargs={'pk': mech_reject_profile.pk}),
            {'action': 'reject', 'rejection_reason': reason},
            follow=True
        )
        self.assertEqual(res_reject.status_code, 200)
        mech_reject_profile.refresh_from_db()
        self.assertEqual(mech_reject_profile.verification_status, MechanicProfile.VerificationStatus.REJECTED)
        self.assertFalse(mech_reject_profile.is_verified)
        self.assertEqual(mech_reject_profile.rejection_reason, reason)

    # 9. Workshop verification: Approve, Reject, and Suspend
    def test_09_workshop_verification_approve_reject_suspend(self):
        self.client.login(username='admin_staff', password=self.password)

        # 9a. Approve workshop
        res_approve = self.client.post(
            reverse('admin_dashboard:workshop_detail', kwargs={'pk': self.workshop.pk}),
            {'action': 'approve'},
            follow=True
        )
        self.assertEqual(res_approve.status_code, 200)
        self.workshop.refresh_from_db()
        self.assertEqual(self.workshop.verification_status, Workshop.VerificationStatus.APPROVED)

        # 9b. Reject workshop
        reason_rej = "Environmental compliance documentation missing."
        res_rej = self.client.post(
            reverse('admin_dashboard:workshop_detail', kwargs={'pk': self.workshop.pk}),
            {'action': 'reject', 'rejection_reason': reason_rej},
            follow=True
        )
        self.assertEqual(res_rej.status_code, 200)
        self.workshop.refresh_from_db()
        self.assertEqual(self.workshop.verification_status, Workshop.VerificationStatus.REJECTED)
        self.assertEqual(self.workshop.rejection_reason, reason_rej)

        # 9c. Suspend workshop and deactivate owner
        reason_susp = "Excessive unresolved customer safety grievances."
        res_susp = self.client.post(
            reverse('admin_dashboard:workshop_detail', kwargs={'pk': self.workshop.pk}),
            {'action': 'suspend', 'rejection_reason': reason_susp, 'deactivate_user': '1'},
            follow=True
        )
        self.assertEqual(res_susp.status_code, 200)
        self.workshop.refresh_from_db()
        self.workshop_user.refresh_from_db()
        self.assertEqual(self.workshop.verification_status, Workshop.VerificationStatus.SUSPENDED)
        self.assertFalse(self.workshop_user.is_active)

    # 10. Supplier verification: Approve, Reject, and Suspend
    def test_10_supplier_verification_approve_reject_suspend(self):
        self.client.login(username='admin_staff', password=self.password)

        # 10a. Approve supplier
        res_approve = self.client.post(
            reverse('admin_dashboard:supplier_detail', kwargs={'pk': self.supplier_profile.pk}),
            {'action': 'approve'},
            follow=True
        )
        self.assertEqual(res_approve.status_code, 200)
        self.supplier_profile.refresh_from_db()
        self.assertEqual(self.supplier_profile.verification_status, SupplierProfile.VerificationStatus.APPROVED)

        # 10b. Reject supplier
        reason_rej = "Tax ID validation failed."
        res_rej = self.client.post(
            reverse('admin_dashboard:supplier_detail', kwargs={'pk': self.supplier_profile.pk}),
            {'action': 'reject', 'rejection_reason': reason_rej},
            follow=True
        )
        self.assertEqual(res_rej.status_code, 200)
        self.supplier_profile.refresh_from_db()
        self.assertEqual(self.supplier_profile.verification_status, SupplierProfile.VerificationStatus.REJECTED)
        self.assertEqual(self.supplier_profile.rejection_reason, reason_rej)

        # 10c. Suspend supplier and deactivate account
        reason_susp = "Distribution of counterfeit components detected."
        res_susp = self.client.post(
            reverse('admin_dashboard:supplier_detail', kwargs={'pk': self.supplier_profile.pk}),
            {'action': 'suspend', 'rejection_reason': reason_susp, 'deactivate_user': '1'},
            follow=True
        )
        self.assertEqual(res_susp.status_code, 200)
        self.supplier_profile.refresh_from_db()
        self.supplier_user.refresh_from_db()
        self.assertEqual(self.supplier_profile.verification_status, SupplierProfile.VerificationStatus.SUSPENDED)
        self.assertFalse(self.supplier_user.is_active)

    # 11. Service request monitoring and SLA overdue detection
    def test_11_service_request_monitoring(self):
        self.client.login(username='admin_staff', password=self.password)

        # List services
        res_list = self.client.get(reverse('admin_dashboard:services'))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, f"#{self.service_request.pk}")

        # Search by ticket ID
        res_search_id = self.client.get(reverse('admin_dashboard:services'), {'q': str(self.service_request.pk)})
        self.assertEqual(res_search_id.status_code, 200)
        self.assertContains(res_search_id, f"#{self.service_request.pk}")

        # Search by customer
        res_search_cust = self.client.get(reverse('admin_dashboard:services'), {'q': 'customer_bob'})
        self.assertEqual(res_search_cust.status_code, 200)
        self.assertContains(res_search_cust, f"#{self.service_request.pk}")

        # Test overdue filter with an overdue ticket
        overdue_req = ServiceRequest.objects.create(
            vehicle=self.vehicle,
            customer=self.owner_user,
            problem_description='Oil pressure emergency light blinking.',
            requested_date=timezone.now() - datetime.timedelta(days=3),
            status=ServiceRequest.Status.PENDING
        )

        res_overdue = self.client.get(reverse('admin_dashboard:services'), {'overdue': '1'})
        self.assertEqual(res_overdue.status_code, 200)
        self.assertContains(res_overdue, f"#{overdue_req.pk}")

        # Inspect ticket details
        res_detail = self.client.get(reverse('admin_dashboard:service_detail', kwargs={'pk': overdue_req.pk}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, "Service SLA Alert: Ticket is Overdue")
        self.assertContains(res_detail, "Oil pressure emergency light blinking")

    # 12. Complaint management and administrative adjudication
    def test_12_complaint_management_and_admin_response(self):
        self.client.login(username='admin_staff', password=self.password)

        complaint = Complaint.objects.create(
            user=self.owner_user,
            service_request=self.service_request,
            subject='Overcharging on brake pad installation',
            description='The bill exceeded the quote by $150 without prior customer approval.',
            status=Complaint.Status.OPEN
        )

        # List complaints
        res_list = self.client.get(reverse('admin_dashboard:complaints'))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, complaint.subject)

        # Inspect complaint
        res_detail = self.client.get(reverse('admin_dashboard:complaint_detail', kwargs={'pk': complaint.pk}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, complaint.subject)

        # Post administrative resolution
        resolution_notes = "Administrative review conducted: Provider refunded $150 overcharge directly to customer card."
        res_post = self.client.post(
            reverse('admin_dashboard:complaint_detail', kwargs={'pk': complaint.pk}),
            {
                'status': Complaint.Status.RESOLVED,
                'admin_response': resolution_notes
            },
            follow=True
        )
        self.assertEqual(res_post.status_code, 200)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.RESOLVED)
        self.assertEqual(complaint.admin_response, resolution_notes)
        self.assertEqual(complaint.resolved_by, self.staff_user)
        self.assertIsNotNone(complaint.resolved_at)

        # Check ActivityLog
        log = ActivityLog.objects.filter(
            action_type=ActivityLog.ActionType.COMPLAINT_UPDATE,
            target_object_id=str(complaint.pk)
        ).first()
        self.assertIsNotNone(log)
        self.assertIn("Updated complaint", log.description)

    # 13. Platform activity logging and privacy protection
    def test_13_platform_activity_logging(self):
        self.client.login(username='admin_staff', password=self.password)

        # Create explicit activity
        log = ActivityLog.objects.create(
            user=self.staff_user,
            action_type=ActivityLog.ActionType.ADMIN_ACTION,
            description="Generated quarterly platform compliance audit report.",
            target_repr="ComplianceReport-Q3"
        )

        res = self.client.get(reverse('admin_dashboard:activities'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Generated quarterly platform compliance audit report")

        # Test search
        res_search = self.client.get(reverse('admin_dashboard:activities'), {'q': 'ComplianceReport-Q3'})
        self.assertEqual(res_search.status_code, 200)
        self.assertContains(res_search, "Generated quarterly platform compliance audit report")

        # Check that no passwords exist in any activity descriptions
        all_logs = ActivityLog.objects.all()
        for l in all_logs:
            self.assertNotIn(self.password, l.description)

    # 14. Existing dashboards remain intact and operational
    def test_14_existing_dashboards_unaffected(self):
        # 14a. Vehicle Owner Dashboard
        self.client.login(username='customer_bob', password=self.password)
        res_owner = self.client.get(reverse('accounts:vehicle_owner_dashboard'))
        self.assertEqual(res_owner.status_code, 200)
        self.client.logout()

        # 14b. Mechanic Dashboard
        self.client.login(username='mechanic_dave', password=self.password)
        res_mech = self.client.get(reverse('mechanics:dashboard'))
        self.assertEqual(res_mech.status_code, 200)
        self.client.logout()

        # 14c. Workshop Dashboard
        self.client.login(username='workshop_tom', password=self.password)
        res_ws = self.client.get(reverse('workshops:dashboard'))
        self.assertEqual(res_ws.status_code, 200)
        self.client.logout()

        # 14d. Supplier Dashboard
        self.client.login(username='supplier_sam', password=self.password)
        res_sup = self.client.get(reverse('suppliers:dashboard'))
        self.assertEqual(res_sup.status_code, 200)
        self.client.logout()
