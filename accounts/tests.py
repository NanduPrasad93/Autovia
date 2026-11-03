from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from accounts.models import UserProfile
from mechanics.models import MechanicProfile
from workshops.models import Workshop
from suppliers.models import SupplierProfile


class AuthenticationAndRBACTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.vehicle_owner_password = 'VehicleOwner@Pass12345!'
        self.mechanic_password = 'Mechanic@Pass12345!'
        self.workshop_password = 'Workshop@Pass12345!'
        self.supplier_password = 'Supplier@Pass12345!'
        self.admin_password = 'Admin@Pass12345!'

        # Create baseline vehicle owner
        self.vehicle_owner = User.objects.create_user(
            username='owner_john',
            email='john@autovia.test',
            password=self.vehicle_owner_password,
            first_name='John',
            last_name='Doe'
        )
        self.vehicle_owner_profile = self.vehicle_owner.profile
        self.vehicle_owner_profile.role = UserProfile.Role.VEHICLE_OWNER
        self.vehicle_owner_profile.phone_number = '1234567890'
        self.vehicle_owner_profile.save()

        # Create baseline mechanic
        self.mechanic_user = User.objects.create_user(
            username='mechanic_mike',
            email='mike@autovia.test',
            password=self.mechanic_password,
            first_name='Mike',
            last_name='Smith'
        )
        self.mechanic_profile = self.mechanic_user.profile
        self.mechanic_profile.role = UserProfile.Role.MECHANIC
        self.mechanic_profile.save()
        MechanicProfile.objects.create(
            user=self.mechanic_user,
            specialization='Brake Systems',
            service_location='Downtown',
            verification_status=MechanicProfile.VerificationStatus.PENDING
        )

        # Create baseline admin
        self.admin_user = User.objects.create_superuser(
            username='admin_boss',
            email='admin@autovia.test',
            password=self.admin_password,
            first_name='Admin',
            last_name='Chief'
        )

    # 1. Vehicle owner registration and login
    def test_01_vehicle_owner_registration_and_login(self):
        reg_data = {
            'full_name': 'Alice Wonder',
            'username': 'alice_w',
            'email': 'alice@autovia.test',
            'phone_number': '5551234567',
            'account_type': UserProfile.Role.VEHICLE_OWNER,
            'password': 'StrongPassword@2026',
            'confirm_password': 'StrongPassword@2026',
        }
        res_reg = self.client.post(reverse('accounts:register'), reg_data, follow=True)
        self.assertEqual(res_reg.status_code, 200)

        # Confirm user and profile in DB
        user = User.objects.get(username='alice_w')
        self.assertEqual(user.profile.role, UserProfile.Role.VEHICLE_OWNER)
        self.assertEqual(user.profile.phone_number, '5551234567')

        # Test login with email
        res_login = self.client.post(reverse('accounts:login'), {
            'username': 'alice@autovia.test',
            'password': 'StrongPassword@2026',
        }, follow=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertTrue(res_login.context['user'].is_authenticated)
        # Should redirect to vehicle owner dashboard
        self.assertRedirects(res_login, reverse('accounts:vehicle_owner_dashboard'))

    # 2. Mechanic registration and pending verification
    def test_02_mechanic_registration_and_pending_verification(self):
        reg_data = {
            'full_name': 'David Miller',
            'username': 'david_mechanic',
            'email': 'david@autovia.test',
            'phone_number': '5559876543',
            'account_type': UserProfile.Role.MECHANIC,
            'password': 'MechanicSecret@123',
            'confirm_password': 'MechanicSecret@123',
        }
        res = self.client.post(reverse('accounts:register'), reg_data, follow=True)
        self.assertEqual(res.status_code, 200)

        user = User.objects.get(username='david_mechanic')
        self.assertEqual(user.profile.role, UserProfile.Role.MECHANIC)

        # Check MechanicProfile automatically created with PENDING verification
        mechanic_entry = MechanicProfile.objects.get(user=user)
        self.assertEqual(mechanic_entry.verification_status, MechanicProfile.VerificationStatus.PENDING)

        # Login and check redirect to mechanic dashboard
        res_login = self.client.post(reverse('accounts:login'), {
            'username': 'david_mechanic',
            'password': 'MechanicSecret@123',
        }, follow=True)
        self.assertRedirects(res_login, reverse('accounts:mechanic_dashboard'))

    # 3. Workshop registration and pending verification
    def test_03_workshop_registration_and_pending_verification(self):
        reg_data = {
            'full_name': 'Apex Motor Works',
            'username': 'apex_motors',
            'email': 'contact@apexmotors.test',
            'phone_number': '5554443322',
            'account_type': UserProfile.Role.WORKSHOP,
            'password': 'WorkshopSecret@123',
            'confirm_password': 'WorkshopSecret@123',
        }
        res = self.client.post(reverse('accounts:register'), reg_data, follow=True)
        self.assertEqual(res.status_code, 200)

        user = User.objects.get(username='apex_motors')
        self.assertEqual(user.profile.role, UserProfile.Role.WORKSHOP)

        # Check Workshop automatically created with PENDING verification
        workshop_entry = Workshop.objects.get(owner=user)
        self.assertEqual(workshop_entry.verification_status, Workshop.VerificationStatus.PENDING)

        # Login and check redirect to workshop dashboard
        res_login = self.client.post(reverse('accounts:login'), {
            'username': 'apex_motors',
            'password': 'WorkshopSecret@123',
        }, follow=True)
        self.assertRedirects(res_login, reverse('accounts:workshop_dashboard'))

    # 4. Supplier registration and pending verification
    def test_04_supplier_registration_and_pending_verification(self):
        reg_data = {
            'full_name': 'Global Spares Corp',
            'username': 'global_spares',
            'email': 'sales@globalspares.test',
            'phone_number': '5557778899',
            'account_type': UserProfile.Role.SUPPLIER,
            'password': 'SupplierSecret@123',
            'confirm_password': 'SupplierSecret@123',
        }
        res = self.client.post(reverse('accounts:register'), reg_data, follow=True)
        self.assertEqual(res.status_code, 200)

        user = User.objects.get(username='global_spares')
        self.assertEqual(user.profile.role, UserProfile.Role.SUPPLIER)

        # Check SupplierProfile automatically created with PENDING verification
        supplier_entry = SupplierProfile.objects.get(user=user)
        self.assertEqual(supplier_entry.verification_status, SupplierProfile.VerificationStatus.PENDING)

        # Login and check redirect to supplier dashboard
        res_login = self.client.post(reverse('accounts:login'), {
            'username': 'global_spares',
            'password': 'SupplierSecret@123',
        }, follow=True)
        self.assertRedirects(res_login, reverse('accounts:supplier_dashboard'))

    # 5. Invalid password
    def test_05_invalid_password_login(self):
        res = self.client.post(reverse('accounts:login'), {
            'username': 'owner_john',
            'password': 'WrongPassword123!',
        })
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.context['user'].is_authenticated)
        self.assertContains(res, "Invalid username/email or password")

    # 6. Duplicate username
    def test_06_duplicate_username_registration(self):
        reg_data = {
            'full_name': 'Another John',
            'username': 'owner_john',  # already exists
            'email': 'anotherjohn@autovia.test',
            'phone_number': '1112223333',
            'account_type': UserProfile.Role.VEHICLE_OWNER,
            'password': 'NewPassword@12345',
            'confirm_password': 'NewPassword@12345',
        }
        res = self.client.post(reverse('accounts:register'), reg_data)
        self.assertEqual(res.status_code, 200)
        self.assertIn('username', res.context['form'].errors)
        self.assertIn("This username is already taken. Please choose another one.", res.context['form'].errors['username'])

    # 7. Duplicate email
    def test_07_duplicate_email_registration(self):
        reg_data = {
            'full_name': 'Johnny Test',
            'username': 'unique_johnny',
            'email': 'john@autovia.test',  # already exists
            'phone_number': '1112223333',
            'account_type': UserProfile.Role.VEHICLE_OWNER,
            'password': 'NewPassword@12345',
            'confirm_password': 'NewPassword@12345',
        }
        res = self.client.post(reverse('accounts:register'), reg_data)
        self.assertEqual(res.status_code, 200)
        self.assertIn('email', res.context['form'].errors)
        self.assertIn("An account with this email address already exists.", res.context['form'].errors['email'])

    # 8. Password mismatch
    def test_08_password_mismatch_registration(self):
        reg_data = {
            'full_name': 'Mismatch Test',
            'username': 'mismatch_user',
            'email': 'mismatch@autovia.test',
            'phone_number': '1112223333',
            'account_type': UserProfile.Role.VEHICLE_OWNER,
            'password': 'FirstPassword@123',
            'confirm_password': 'DifferentPassword@123',
        }
        res = self.client.post(reverse('accounts:register'), reg_data)
        self.assertEqual(res.status_code, 200)
        self.assertIn('confirm_password', res.context['form'].errors)
        self.assertIn("Passwords do not match.", res.context['form'].errors['confirm_password'])

    # 9. Logout
    def test_09_secure_logout(self):
        self.client.login(username='owner_john', password=self.vehicle_owner_password)
        res_check = self.client.get(reverse('accounts:vehicle_owner_dashboard'))
        self.assertEqual(res_check.status_code, 200)

        # POST logout
        res_logout = self.client.post(reverse('accounts:logout'), follow=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertFalse(res_logout.context['user'].is_authenticated)

    # 10. Unauthorized dashboard access
    def test_10_unauthorized_dashboard_access(self):
        # Log in as Vehicle Owner
        self.client.login(username='owner_john', password=self.vehicle_owner_password)

        # Attempt to access Mechanic Dashboard -> Expect 403 Forbidden
        res_mech = self.client.get(reverse('accounts:mechanic_dashboard'))
        self.assertEqual(res_mech.status_code, 403)

        # Attempt to access Supplier Dashboard -> Expect 403 Forbidden
        res_supp = self.client.get(reverse('accounts:supplier_dashboard'))
        self.assertEqual(res_supp.status_code, 403)

        # Attempt to access Admin Dashboard -> Expect 403 Forbidden
        res_adm = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(res_adm.status_code, 403)

    # 11. Anonymous user accessing protected pages
    def test_11_anonymous_user_access_protection(self):
        protected_urls = [
            reverse('accounts:vehicle_owner_dashboard'),
            reverse('accounts:mechanic_dashboard'),
            reverse('accounts:workshop_dashboard'),
            reverse('accounts:supplier_dashboard'),
            reverse('accounts:admin_dashboard'),
        ]
        for url in protected_urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 302, f"URL {url} did not redirect anonymous user")
            self.assertIn(reverse('accounts:login'), res.url)

    # 12. Attempted public ADMIN registration
    def test_12_attempted_public_admin_registration(self):
        reg_data = {
            'full_name': 'Hacker Admin',
            'username': 'fake_admin',
            'email': 'hacker@autovia.test',
            'phone_number': '0000000000',
            'account_type': 'ADMIN',
            'password': 'HackerPassword@123',
            'confirm_password': 'HackerPassword@123',
        }
        res = self.client.post(reverse('accounts:register'), reg_data)
        self.assertEqual(res.status_code, 200)
        self.assertIn('account_type', res.context['form'].errors)
        self.assertFalse(User.objects.filter(username='fake_admin').exists())

    # 13. Password reset workflow
    def test_13_password_reset_workflow(self):
        # 1. Request password reset
        mail.outbox = []
        res = self.client.post(reverse('accounts:password_reset'), {
            'email': 'john@autovia.test',
        }, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertRedirects(res, reverse('accounts:password_reset_done'))

        # Check console email generated
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('john@autovia.test', email.to)
        self.assertIn('password-reset-confirm', email.body)
