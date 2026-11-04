from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from decimal import Decimal

from accounts.models import UserProfile, Complaint, ActivityLog
from vehicles.models import Vehicle
from mechanics.models import MechanicProfile
from workshops.models import Workshop
from suppliers.models import SupplierProfile, SparePart, SparePartOrder, SparePartOrderItem
from services.models import ServiceRequest, RepairEstimate, RepairBill, ServiceFeedback, ServiceRecord
from expenses.models import Expense


class AutoViaEndToEndIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'AutoVia@Integration2026!'

        # 1. Administrator
        self.admin = User.objects.create_superuser(
            username='admin_boss',
            email='admin@autovia.test',
            password=self.password
        )
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save()

        # 2. Vehicle Owner
        self.owner = User.objects.create_user(
            username='owner_dan',
            email='dan@autovia.test',
            password=self.password,
            first_name='Dan',
            last_name='Driver'
        )
        self.owner.profile.role = UserProfile.Role.VEHICLE_OWNER
        self.owner.profile.save()

        # 3. Mechanic User & Verified Profile
        self.mechanic_user = User.objects.create_user(
            username='mechanic_mark',
            email='mark@autovia.test',
            password=self.password,
            first_name='Mark',
            last_name='Mechanic'
        )
        self.mechanic_user.profile.role = UserProfile.Role.MECHANIC
        self.mechanic_user.profile.save()
        self.mechanic_profile = MechanicProfile.objects.create(
            user=self.mechanic_user,
            specialization='Brakes & Suspension',
            service_location='Central City',
            experience_years=7,
            verification_status=MechanicProfile.VerificationStatus.VERIFIED
        )

        # 4. Workshop User & Approved Workshop
        self.workshop_user = User.objects.create_user(
            username='workshop_walter',
            email='walter@autovia.test',
            password=self.password,
            first_name='Walter',
            last_name='Workshop'
        )
        self.workshop_user.profile.role = UserProfile.Role.WORKSHOP
        self.workshop_user.profile.save()
        self.workshop = Workshop.objects.create(
            owner=self.workshop_user,
            workshop_name='Precision Auto Centre',
            address='404 Industrial Ring',
            verification_status=Workshop.VerificationStatus.APPROVED
        )

        # 5. Supplier User & Profile
        self.supplier_user = User.objects.create_user(
            username='supplier_steve',
            email='steve@autovia.test',
            password=self.password,
            first_name='Steve',
            last_name='Supplier'
        )
        self.supplier_user.profile.role = UserProfile.Role.SUPPLIER
        self.supplier_user.profile.save()
        self.supplier_profile = SupplierProfile.objects.create(
            user=self.supplier_user,
            business_name='Apex OEM Components',
            business_address='77 Parts Highway',
            phone_number='5551112222',
            verification_status=SupplierProfile.VerificationStatus.PENDING
        )

    # WORKFLOW A: Vehicle Owner and Mechanic
    def test_workflow_a_owner_and_mechanic(self):
        # 1. Owner registers a vehicle
        self.client.login(username='owner_dan', password=self.password)
        res_veh = self.client.post(reverse('vehicles:add'), {
            'registration_number': 'AUTO-INT-001',
            'manufacturer': 'Honda',
            'model_name': 'Civic Touring',
            'manufacturing_year': 2022,
            'fuel_type': 'PETROL',
            'color': 'Aegean Blue',
            'current_odometer': 18500,
        }, follow=True)
        self.assertEqual(res_veh.status_code, 200)
        vehicle = Vehicle.objects.get(registration_number='AUTO-INT-001')
        self.assertEqual(vehicle.owner, self.owner)

        # 2. Owner browses mechanics directory
        res_dir = self.client.get(reverse('mechanics:find_mechanics'))
        self.assertEqual(res_dir.status_code, 200)
        self.assertContains(res_dir, "Mark Mechanic")

        # 3. Owner submits service request to Mechanic Mark
        res_req = self.client.post(reverse('services:request_create'), {
            'vehicle': vehicle.pk,
            'mechanic': self.mechanic_profile.pk,
            'problem_description': 'Front brake pads grinding and rotor squeal.',
            'requested_date': (timezone.now() + datetime.timedelta(days=2)).strftime('%Y-%m-%dT%H:%M'),
        }, follow=True)
        self.assertEqual(res_req.status_code, 200)
        service_req = ServiceRequest.objects.get(vehicle=vehicle, mechanic=self.mechanic_profile)
        self.assertEqual(service_req.status, ServiceRequest.Status.PENDING)
        self.client.logout()

        # 4. Mechanic inspects incoming requests and accepts
        self.client.login(username='mechanic_mark', password=self.password)
        res_m_list = self.client.get(reverse('mechanics:incoming_requests'))
        self.assertEqual(res_m_list.status_code, 200)
        self.assertContains(res_m_list, f"#{service_req.pk}")

        # Accept request
        res_accept = self.client.post(reverse('mechanics:accept_request', kwargs={'pk': service_req.pk}), follow=True)
        self.assertEqual(res_accept.status_code, 200)
        service_req.refresh_from_db()
        self.assertEqual(service_req.status, ServiceRequest.Status.ACCEPTED)

        # 5. Mechanic updates status to IN_PROGRESS
        res_prog = self.client.post(reverse('mechanics:update_repair_status', kwargs={'pk': service_req.pk}), {
            'status': ServiceRequest.Status.IN_PROGRESS,
            'notes': 'Brake rotors resurfaced and ceramic pads installed.'
        }, follow=True)
        self.assertEqual(res_prog.status_code, 200)
        service_req.refresh_from_db()
        self.assertEqual(service_req.status, ServiceRequest.Status.IN_PROGRESS)

        # 6. Mechanic completes repair and generates final bill
        res_bill = self.client.post(reverse('mechanics:generate_bill', kwargs={'pk': service_req.pk}), {
            'service_date': timezone.now().date().isoformat(),
            'labor_charges': '120.00',
            'parts_charges': '85.00',
            'additional_charges': '10.00',
            'service_description': 'Front brake pads replacement and rotor machining',
            'payment_method': 'CARD',
            'is_paid': True,
        }, follow=True)
        self.assertEqual(res_bill.status_code, 200)
        service_req.refresh_from_db()
        self.assertEqual(service_req.status, ServiceRequest.Status.COMPLETED)
        self.assertTrue(hasattr(service_req, 'bill'))
        self.assertEqual(service_req.bill.total_amount, Decimal('215.00'))
        self.client.logout()

        # 7. Customer inspects completed bill and submits 5-star feedback
        self.client.login(username='owner_dan', password=self.password)
        res_cust_bill = self.client.get(reverse('services:customer_bill_detail', kwargs={'pk': service_req.pk}))
        self.assertEqual(res_cust_bill.status_code, 200)
        self.assertContains(res_cust_bill, "$215.00")

        res_fb = self.client.post(reverse('services:submit_feedback', kwargs={'pk': service_req.pk}), {
            'rating': 5,
            'comment': 'Outstanding and fast brake service! Zero noise now.',
        }, follow=True)
        self.assertEqual(res_fb.status_code, 200)
        self.assertTrue(ServiceFeedback.objects.filter(service_request=service_req, rating=5).exists())

    # WORKFLOW B: Vehicle Owner and Workshop
    def test_workflow_b_owner_and_workshop(self):
        # 1. Create vehicle
        vehicle = Vehicle.objects.create(
            owner=self.owner,
            registration_number='WS-INT-002',
            manufacturer='Subaru',
            model_name='Outback',
            manufacturing_year=2021,
            fuel_type='PETROL',
            color='Wilderness Green',
            current_odometer=32000
        )

        # 2. Owner submits workshop request
        self.client.login(username='owner_dan', password=self.password)
        res_req = self.client.post(reverse('services:request_create'), {
            'vehicle': vehicle.pk,
            'workshop': self.workshop.pk,
            'problem_description': 'All-wheel drive differential fluid flush and tire rotation.',
            'requested_date': (timezone.now() + datetime.timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
        }, follow=True)
        self.assertEqual(res_req.status_code, 200)
        req = ServiceRequest.objects.get(vehicle=vehicle, workshop=self.workshop)
        self.client.logout()

        # 3. Workshop receives request and submits estimate
        self.client.login(username='workshop_walter', password=self.password)
        # Accept
        self.client.post(reverse('workshops:accept_request', kwargs={'pk': req.pk}), follow=True)
        req.refresh_from_db()
        self.assertEqual(req.status, ServiceRequest.Status.ACCEPTED)

        # Prepare estimate
        res_est = self.client.post(reverse('workshops:create_estimate', kwargs={'pk': req.pk}), {
            'labor_cost': '150.00',
            'parts_cost': '110.00',
            'additional_cost': '15.00',
            'estimated_completion_date': (timezone.now().date() + datetime.timedelta(days=4)).isoformat(),
            'description': 'OEM synthetic gear oil and 4-wheel rotation',
        }, follow=True)
        self.assertEqual(res_est.status_code, 200)
        self.assertTrue(RepairEstimate.objects.filter(service_request=req).exists())

        # Progress repair to IN_PROGRESS
        res_prog = self.client.post(reverse('workshops:update_repair_status', kwargs={'pk': req.pk}), {
            'status': ServiceRequest.Status.IN_PROGRESS,
            'notes': 'Differential disassembled and inspected in Bay 3.'
        }, follow=True)
        self.assertEqual(res_prog.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.status, ServiceRequest.Status.IN_PROGRESS)

        # Generate official repair bill and complete service
        res_bill = self.client.post(reverse('workshops:generate_bill', kwargs={'pk': req.pk}), {
            'service_date': timezone.now().date().isoformat(),
            'labor_charges': '150.00',
            'parts_charges': '110.00',
            'additional_charges': '15.00',
            'service_description': 'OEM synthetic gear oil and 4-wheel rotation',
            'payment_method': 'CARD',
            'is_paid': True,
        }, follow=True)
        self.assertEqual(res_bill.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.status, ServiceRequest.Status.COMPLETED)
        self.client.logout()

        # 4. Customer views service history record
        self.client.login(username='owner_dan', password=self.password)
        res_hist = self.client.get(reverse('services:history_list'))
        self.assertEqual(res_hist.status_code, 200)
        self.assertContains(res_hist, "WS-INT-002")

    # WORKFLOW C: Spare Parts Supplier & Inventory Lifecycle
    def test_workflow_c_supplier_order_and_stock_lifecycle(self):
        # 1. Admin verifies supplier
        self.client.login(username='admin_boss', password=self.password)
        res_v = self.client.post(
            reverse('admin_dashboard:supplier_detail', kwargs={'pk': self.supplier_profile.pk}),
            {'action': 'approve'},
            follow=True
        )
        self.assertEqual(res_v.status_code, 200)
        self.supplier_profile.refresh_from_db()
        self.assertTrue(self.supplier_profile.is_approved)
        self.client.logout()

        # 2. Approved Supplier adds spare part to catalog
        self.client.login(username='supplier_steve', password=self.password)
        res_add = self.client.post(reverse('suppliers:product_add'), {
            'part_name': 'Ceramic Performance Brake Pad Set',
            'part_number': 'CP-PADS-2026',
            'compatible_manufacturer': 'Honda',
            'compatible_vehicle_models': 'Civic (2020-2024), Accord (2018-2023)',
            'price': '85.00',
            'stock_quantity': 20,
            'is_available': True,
            'description': 'High heat dissipation low-dust ceramic pads.',
        }, follow=True)
        self.assertEqual(res_add.status_code, 200)
        part = SparePart.objects.get(part_number='CP-PADS-2026')
        self.assertEqual(part.stock_quantity, 20)

        # 3. Customer places order for 3 sets
        order = SparePartOrder.objects.create(
            customer=self.owner,
            shipping_address='123 Main St, Springfield',
            contact_phone='5551234567',
            status=SparePartOrder.Status.PENDING,
            total_amount=Decimal('255.00')
        )
        item = SparePartOrderItem.objects.create(
            order=order,
            part=part,
            quantity=3,
            unit_price=Decimal('85.00')
        )

        # 4. Supplier confirms order -> stock safely deducted (20 - 3 = 17)
        res_conf = self.client.post(
            reverse('suppliers:update_order_status', kwargs={'pk': order.pk}),
            {'status': SparePartOrder.Status.CONFIRMED},
            follow=True
        )
        self.assertEqual(res_conf.status_code, 200)
        part.refresh_from_db()
        self.assertEqual(part.stock_quantity, 17)

        # 5. Supplier delivers order -> status DELIVERED
        res_deliv = self.client.post(
            reverse('suppliers:update_order_status', kwargs={'pk': order.pk}),
            {'status': SparePartOrder.Status.DELIVERED},
            follow=True
        )
        self.assertEqual(res_deliv.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, SparePartOrder.Status.DELIVERED)

    # WORKFLOW D: Admin Accreditation, Monitoring, and Grievance Resolution
    def test_workflow_d_admin_accreditation_and_complaint_adjudication(self):
        self.client.login(username='admin_boss', password=self.password)

        # Admin Overview
        res_dash = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(res_dash.status_code, 200)
        self.assertContains(res_dash, "AutoVia Administration")

        # Admin lists users
        res_users = self.client.get(reverse('admin_dashboard:users'))
        self.assertEqual(res_users.status_code, 200)
        self.assertContains(res_users, "owner_dan")

        # File a complaint as owner and adjudicate as admin
        complaint = Complaint.objects.create(
            user=self.owner,
            subject='Delayed order delivery investigation',
            description='Tracking package indicated shipment delayed by carrier.',
            status=Complaint.Status.OPEN
        )

        res_cmp = self.client.post(
            reverse('admin_dashboard:complaint_detail', kwargs={'pk': complaint.pk}),
            {
                'status': Complaint.Status.RESOLVED,
                'admin_response': 'Carrier expedited shipment and customer received tracking confirmation.'
            },
            follow=True
        )
        self.assertEqual(res_cmp.status_code, 200)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.RESOLVED)
        self.assertEqual(complaint.resolved_by, self.admin)

        # Platform activity logged
        res_act = self.client.get(reverse('admin_dashboard:activities'))
        self.assertEqual(res_act.status_code, 200)
        self.assertContains(res_act, "Updated complaint")

    # WORKFLOW E: Vehicle Expenses, Analytics, and CSV Export
    def test_workflow_e_vehicle_expenses_and_analytics(self):
        vehicle = Vehicle.objects.create(
            owner=self.owner,
            registration_number='EXP-INT-005',
            manufacturer='Mazda',
            model_name='CX-5',
            manufacturing_year=2023,
            fuel_type='PETROL',
            color='Soul Red Crystal',
            current_odometer=12000
        )

        self.client.login(username='owner_dan', password=self.password)

        # Log fuel expense
        res_add = self.client.post(reverse('expenses:add'), {
            'vehicle': vehicle.pk,
            'category': Expense.Category.FUEL,
            'amount': '55.00',
            'expense_date': timezone.now().date().isoformat(),
            'description': 'Full tank 95 Unleaded fuel',
        }, follow=True)
        self.assertEqual(res_add.status_code, 200)

        # Check analytics dashboard updates
        res_analytics = self.client.get(reverse('expenses:analytics'))
        self.assertEqual(res_analytics.status_code, 200)
        self.assertContains(res_analytics, "$55.00")
        self.assertContains(res_analytics, "CX-5")

        # Export CSV report
        res_csv = self.client.get(reverse('expenses:export_csv'))
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn('EXP-INT-005', res_csv.content.decode('utf-8'))
        self.assertIn('55.00', res_csv.content.decode('utf-8'))
