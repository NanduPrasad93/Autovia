from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone

from accounts.models import UserProfile
from suppliers.models import SupplierProfile, SparePart, SparePartOrder, SparePartOrderItem


class SupplierPortalTests(TestCase):
    """
    Comprehensive test suite for STEP 10: Spare Parts Supplier Dashboard.
    Validates RBAC, verification gating, catalog CRUD, search/filter/sort,
    inventory stock console, order fulfillment, atomic stock deduction & restoration,
    IDOR security, sales calculations, and non-supplier access rejection.
    """

    def setUp(self):
        self.client = Client()

        # 1. Primary Supplier User A
        self.supplier_user = User.objects.create_user(
            username='apex_parts',
            email='apex@partswholesale.com',
            password='Supplier@Pass123!',
            first_name='Apex',
            last_name='Components'
        )
        self.supplier_user_profile, _ = UserProfile.objects.get_or_create(user=self.supplier_user)
        self.supplier_user_profile.role = UserProfile.Role.SUPPLIER
        self.supplier_user_profile.phone_number = '+1-555-019-5501'
        self.supplier_user_profile.save()

        self.supplier = SupplierProfile.objects.create(
            user=self.supplier_user,
            business_name='Apex OEM Auto Parts Distribution',
            business_address='742 Industrial Expressway, Hub 9',
            phone_number='+1-555-019-5501',
            description='Authorized wholesale distributor for Japanese and German automotive OEM parts.',
            verification_status=SupplierProfile.VerificationStatus.APPROVED
        )

        # 2. Secondary Supplier User B (for IDOR and isolation checks)
        self.supplier_user_b = User.objects.create_user(
            username='metro_spares',
            email='metro@spares.com',
            password='SupplierB@Pass123!',
            first_name='Metro',
            last_name='Spares'
        )
        self.supplier_user_profile_b, _ = UserProfile.objects.get_or_create(user=self.supplier_user_b)
        self.supplier_user_profile_b.role = UserProfile.Role.SUPPLIER
        self.supplier_user_profile_b.phone_number = '+1-555-019-5502'
        self.supplier_user_profile_b.save()

        self.supplier_b = SupplierProfile.objects.create(
            user=self.supplier_user_b,
            business_name='Metro Performance Parts Ltd',
            business_address='100 Logistics Way, Bay 3',
            phone_number='+1-555-019-5502',
            description='Performance aftermarket exhaust, turbochargers, and suspension.',
            verification_status=SupplierProfile.VerificationStatus.APPROVED
        )

        # 3. Vehicle Owner / Customer User
        self.customer = User.objects.create_user(
            username='car_owner_lisa',
            email='lisa@example.com',
            password='Customer@Pass123!',
            first_name='Lisa',
            last_name='Ray'
        )
        self.customer_profile, _ = UserProfile.objects.get_or_create(user=self.customer)
        self.customer_profile.role = UserProfile.Role.VEHICLE_OWNER
        self.customer_profile.phone_number = '+1-555-019-3301'
        self.customer_profile.save()

        # 4. Mechanic User (for role-based access denial test)
        self.mechanic_user = User.objects.create_user(
            username='sam_mechanic',
            email='sam@mechanic.com',
            password='Mechanic@Pass123!',
            first_name='Sam',
            last_name='Tools'
        )
        self.mechanic_profile, _ = UserProfile.objects.get_or_create(user=self.mechanic_user)
        self.mechanic_profile.role = UserProfile.Role.MECHANIC
        self.mechanic_profile.save()

        # 5. Baseline Spare Parts for Supplier A
        self.part1 = SparePart.objects.create(
            supplier=self.supplier,
            part_name='Ceramic Front Brake Pads',
            part_number='BP-TY-2024-F',
            compatible_manufacturer='Toyota',
            compatible_vehicle_models='RAV4 (2019-2024), Camry (2018-2023)',
            price=Decimal('4500.00'),
            stock_quantity=20,
            is_available=True,
            description='Low-dust ceramic composite front brake pad kit.'
        )

        self.part2 = SparePart.objects.create(
            supplier=self.supplier,
            part_name='Synthetic Engine Oil Filter',
            part_number='OF-UNIV-99',
            compatible_manufacturer='Universal',
            compatible_vehicle_models='Multi-vehicle universal fitment',
            price=Decimal('850.00'),
            stock_quantity=4,  # Low stock (<= 5)
            is_available=True,
            description='High efficiency oil filter for synthetic blends.'
        )

        self.part3 = SparePart.objects.create(
            supplier=self.supplier,
            part_name='Alternator 130A',
            part_number='ALT-HD-2022',
            compatible_manufacturer='Honda',
            compatible_vehicle_models='Honda Civic, CR-V (2016-2022)',
            price=Decimal('12500.00'),
            stock_quantity=0,  # Out of stock
            is_available=True,
            description='High output replacement alternator assembly.'
        )

        # Baseline Spare Part for Supplier B
        self.part_b = SparePart.objects.create(
            supplier=self.supplier_b,
            part_name='Sport Coilover Kit',
            part_number='COIL-METRO-01',
            compatible_manufacturer='Subaru',
            compatible_vehicle_models='WRX / STI (2015-2021)',
            price=Decimal('65000.00'),
            stock_quantity=5,
            is_available=True,
            description='Adjustable damping sport coilovers.'
        )

    # -------------------------------------------------------------
    # Test 1: Supplier Login and Dashboard Access
    # -------------------------------------------------------------
    def test_01_supplier_login_and_dashboard_access(self):
        login_success = self.client.login(username='apex_parts', password='Supplier@Pass123!')
        self.assertTrue(login_success)

        # Test both /supplier/ and /supplier/dashboard/
        for url in ['/supplier/', '/supplier/dashboard/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Apex OEM Auto Parts Distribution')
            self.assertContains(response, 'Synthetic Engine Oil Filter')
            self.assertEqual(response.context['total_products'], 3)
            self.assertEqual(response.context['available_stock'], 24)
            self.assertEqual(response.context['low_stock_count'], 2)  # part2 (4) and part3 (0)

        # Catalog page contains all products including normal stock parts
        res_cat = self.client.get(reverse('suppliers:products'))
        self.assertEqual(res_cat.status_code, 200)
        self.assertContains(res_cat, 'Ceramic Front Brake Pads')

    # -------------------------------------------------------------
    # Test 2: Profile Editing and Verification Protection
    # -------------------------------------------------------------
    def test_02_supplier_profile_editing_and_verification_protection(self):
        self.client.login(username='apex_parts', password='Supplier@Pass123!')

        # Ensure verification cannot be altered through profile form post
        self.supplier.verification_status = SupplierProfile.VerificationStatus.PENDING
        self.supplier.save()

        post_data = {
            'business_name': 'Apex Global Automotive Logistics',
            'contact_email': 'contact@apexlogistics.com',
            'phone_number': '+1-555-999-8888',
            'business_address': 'Building 12, Logistics Park Central',
            'description': 'Updated description of OEM distribution network.',
            'verification_status': 'APPROVED',  # Attempted privilege escalation
        }

        response = self.client.post(reverse('suppliers:profile'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.business_name, 'Apex Global Automotive Logistics')
        self.assertEqual(self.supplier.phone_number, '+1-555-999-8888')
        self.assertEqual(self.supplier.business_address, 'Building 12, Logistics Park Central')
        # Verification status MUST remain PENDING
        self.assertEqual(self.supplier.verification_status, SupplierProfile.VerificationStatus.PENDING)

        # User email must be synchronized
        self.supplier_user.refresh_from_db()
        self.assertEqual(self.supplier_user.email, 'contact@apexlogistics.com')

    # -------------------------------------------------------------
    # Test 3: Add Spare Part Validation (Price > 0, Stock >= 0, Unique Part Number)
    # -------------------------------------------------------------
    def test_03_add_spare_part_validation(self):
        self.client.login(username='apex_parts', password='Supplier@Pass123!')

        # 1. Valid Spare Part Addition
        valid_data = {
            'part_name': 'Timing Belt Water Pump Kit',
            'part_number': 'TB-TY-3030',
            'compatible_manufacturer': 'Toyota',
            'compatible_vehicle_models': 'Highlander, Sienna 3.5L V6',
            'price': '8200.00',
            'stock_quantity': '15',
            'is_available': 'on',
            'description': 'Complete timing component kit with tensioner and water pump.'
        }
        response = self.client.post(reverse('suppliers:product_add'), valid_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SparePart.objects.filter(part_number='TB-TY-3030', supplier=self.supplier).exists())

        # 2. Invalid Price (<= 0)
        invalid_price_data = valid_data.copy()
        invalid_price_data['part_number'] = 'TB-INVALID-PRICE'
        invalid_price_data['price'] = '0.00'
        res_price = self.client.post(reverse('suppliers:product_add'), invalid_price_data)
        self.assertFormError(res_price.context['form'], 'price', 'Product price must be greater than zero.')

        # 3. Invalid Stock (< 0)
        invalid_stock_data = valid_data.copy()
        invalid_stock_data['part_number'] = 'TB-INVALID-STOCK'
        invalid_stock_data['stock_quantity'] = '-5'
        res_stock = self.client.post(reverse('suppliers:product_add'), invalid_stock_data)
        self.assertFormError(res_stock.context['form'], 'stock_quantity', 'Ensure this value is greater than or equal to 0.')

        # 4. Duplicate Part Number (already exists in catalog)
        duplicate_sku_data = valid_data.copy()
        duplicate_sku_data['part_number'] = 'BP-TY-2024-F'  # Same as self.part1
        res_dup = self.client.post(reverse('suppliers:product_add'), duplicate_sku_data)
        self.assertFormError(
            res_dup.context['form'], 'part_number',
            "A product with Part Number 'BP-TY-2024-F' is already registered in the catalog."
        )

    # -------------------------------------------------------------
    # Test 4: Edit and Delete Spare Part (Active Order Protection)
    # -------------------------------------------------------------
    def test_04_edit_and_delete_spare_part(self):
        self.client.login(username='apex_parts', password='Supplier@Pass123!')

        # 1. Edit existing part
        edit_data = {
            'part_name': 'Ceramic Front Brake Pads Pro Edition',
            'part_number': 'BP-TY-2024-F',
            'compatible_manufacturer': 'Toyota & Lexus',
            'compatible_vehicle_models': 'RAV4, Camry, Lexus ES350',
            'price': '4950.00',
            'stock_quantity': '25',
            'is_available': 'on',
            'description': 'Upgraded endurance formulation.'
        }
        res_edit = self.client.post(reverse('suppliers:product_edit', args=[self.part1.pk]), edit_data, follow=True)
        self.assertEqual(res_edit.status_code, 200)
        self.part1.refresh_from_db()
        self.assertEqual(self.part1.part_name, 'Ceramic Front Brake Pads Pro Edition')
        self.assertEqual(self.part1.price, Decimal('4950.00'))
        self.assertEqual(self.part1.stock_quantity, 25)

        # 2. Deletion blocked when involved in active orders
        order = SparePartOrder.objects.create(
            customer=self.customer,
            shipping_address='45 Lake View Lane, Apt 2B',
            contact_phone='+1-555-019-3301',
            total_amount=Decimal('4950.00'),
            status=SparePartOrder.Status.PROCESSING
        )
        SparePartOrderItem.objects.create(
            order=order,
            part=self.part1,
            quantity=1,
            unit_price=self.part1.price,
            stock_deducted=True
        )

        res_del_blocked = self.client.post(reverse('suppliers:product_delete', args=[self.part1.pk]), follow=True)
        self.assertEqual(res_del_blocked.status_code, 200)
        # Part should NOT be deleted
        self.assertTrue(SparePart.objects.filter(pk=self.part1.pk).exists())
        self.assertContains(res_del_blocked, 'Cannot delete')

        # 3. Successful deletion when no active orders exist
        standalone_part = SparePart.objects.create(
            supplier=self.supplier,
            part_name='Cabin Air Filter',
            part_number='CAF-STANDALONE',
            compatible_manufacturer='Nissan',
            price=Decimal('500.00'),
            stock_quantity=10,
            is_available=True
        )
        res_del_success = self.client.post(reverse('suppliers:product_delete', args=[standalone_part.pk]), follow=True)
        self.assertEqual(res_del_success.status_code, 200)
        self.assertFalse(SparePart.objects.filter(pk=standalone_part.pk).exists())

    # -------------------------------------------------------------
    # Test 5: Inventory Search, Filter, and Sort
    # -------------------------------------------------------------
    def test_05_inventory_search_filter_sort(self):
        self.client.login(username='apex_parts', password='Supplier@Pass123!')

        # 1. Search by SKU
        res_q = self.client.get(reverse('suppliers:products') + '?q=OF-UNIV')
        self.assertEqual(res_q.status_code, 200)
        self.assertContains(res_q, 'Synthetic Engine Oil Filter')
        self.assertNotContains(res_q, 'Ceramic Front Brake Pads')

        # 2. Filter by stock=low
        res_low = self.client.get(reverse('suppliers:products') + '?stock=low')
        self.assertContains(res_low, 'Synthetic Engine Oil Filter')  # stock=4
        self.assertNotContains(res_low, 'Ceramic Front Brake Pads')  # stock=20
        self.assertNotContains(res_low, 'Alternator 130A')  # stock=0

        # 3. Filter by stock=out
        res_out = self.client.get(reverse('suppliers:products') + '?stock=out')
        self.assertContains(res_out, 'Alternator 130A')
        self.assertNotContains(res_out, 'Ceramic Front Brake Pads')

        # 4. Filter by manufacturer
        res_mfg = self.client.get(reverse('suppliers:products') + '?mfg=Toyota')
        self.assertContains(res_mfg, 'Ceramic Front Brake Pads')
        self.assertNotContains(res_mfg, 'Alternator 130A')

        # 5. Sort by price descending
        res_sort = self.client.get(reverse('suppliers:products') + '?sort=price_desc')
        products_in_context = list(res_sort.context['products'])
        self.assertEqual(products_in_context[0].part_name, 'Alternator 130A')  # 12500
        self.assertEqual(products_in_context[-1].part_name, 'Synthetic Engine Oil Filter')  # 850

    # -------------------------------------------------------------
    # Test 6: Low Stock Alerts and Inventory Stock Console
    # -------------------------------------------------------------
    def test_06_low_stock_alerts(self):
        self.client.login(username='apex_parts', password='Supplier@Pass123!')

        res_inv = self.client.get(reverse('suppliers:inventory'))
        self.assertEqual(res_inv.status_code, 200)
        self.assertContains(res_inv, 'Synthetic Engine Oil Filter')
        self.assertContains(res_inv, 'Alternator 130A')
        self.assertEqual(res_inv.context['low_stock'].count(), 1)  # stock_quantity=4
        self.assertEqual(res_inv.context['out_of_stock'].count(), 1)  # stock_quantity=0
        self.assertEqual(res_inv.context['adequate_stock'].count(), 1)  # stock_quantity=20

    # -------------------------------------------------------------
    # Test 7: View Incoming Purchase Orders (Supplier Specific Scoping)
    # -------------------------------------------------------------
    def test_07_view_incoming_orders(self):
        # Create multi-supplier purchase order
        order = SparePartOrder.objects.create(
            customer=self.customer,
            shipping_address='77 Skyline Boulevard, Suite 500',
            contact_phone='+1-555-019-3301',
            total_amount=Decimal('69500.00'),
            status=SparePartOrder.Status.PENDING
        )
        # Item 1 from Supplier A (part1: 4500 * 1 = 4500)
        item1 = SparePartOrderItem.objects.create(
            order=order,
            part=self.part1,
            quantity=1,
            unit_price=self.part1.price
        )
        # Item 2 from Supplier B (part_b: 65000 * 1 = 65000)
        item2 = SparePartOrderItem.objects.create(
            order=order,
            part=self.part_b,
            quantity=1,
            unit_price=self.part_b.price
        )

        # Login as Supplier A
        self.client.login(username='apex_parts', password='Supplier@Pass123!')
        res_orders = self.client.get(reverse('suppliers:orders'))
        self.assertEqual(res_orders.status_code, 200)
        self.assertContains(res_orders, f'#{order.pk}')

        # Inspect order detail view
        res_detail = self.client.get(reverse('suppliers:order_detail', args=[order.pk]))
        self.assertEqual(res_detail.status_code, 200)
        # Supplier A should see their brake pads and subtotal 4500
        self.assertContains(res_detail, 'Ceramic Front Brake Pads')
        self.assertEqual(res_detail.context['supplier_subtotal'], Decimal('4500.00'))
        # Supplier A must NOT see Supplier B's items in their itemized table
        self.assertNotContains(res_detail, 'Sport Coilover Kit')

    # -------------------------------------------------------------
    # Test 8: Order Status Progression
    # -------------------------------------------------------------
    def test_08_update_order_statuses(self):
        self.client.login(username='apex_parts', password='Supplier@Pass123!')

        order = SparePartOrder.objects.create(
            customer=self.customer,
            shipping_address='10 Pine Street',
            contact_phone='+1-555-019-3301',
            total_amount=Decimal('4500.00'),
            status=SparePartOrder.Status.PENDING
        )
        item = SparePartOrderItem.objects.create(
            order=order,
            part=self.part1,
            quantity=2,
            unit_price=self.part1.price
        )

        # PENDING -> CONFIRMED
        res_confirm = self.client.post(
            reverse('suppliers:update_order_status', args=[order.pk]),
            {'status': SparePartOrder.Status.CONFIRMED},
            follow=True
        )
        self.assertEqual(res_confirm.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, SparePartOrder.Status.CONFIRMED)

        # CONFIRMED -> PROCESSING
        res_proc = self.client.post(
            reverse('suppliers:update_order_status', args=[order.pk]),
            {'status': SparePartOrder.Status.PROCESSING},
            follow=True
        )
        self.assertEqual(res_proc.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, SparePartOrder.Status.PROCESSING)

        # PROCESSING -> SHIPPED
        res_ship = self.client.post(
            reverse('suppliers:update_order_status', args=[order.pk]),
            {'status': SparePartOrder.Status.SHIPPED},
            follow=True
        )
        self.assertEqual(res_ship.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, SparePartOrder.Status.SHIPPED)

        # SHIPPED -> DELIVERED
        res_del = self.client.post(
            reverse('suppliers:update_order_status', args=[order.pk]),
            {'status': SparePartOrder.Status.DELIVERED},
            follow=True
        )
        self.assertEqual(res_del.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, SparePartOrder.Status.DELIVERED)

    # -------------------------------------------------------------
    # Test 9: Prevent Order Exceeding Available Physical Stock
    # -------------------------------------------------------------
    def test_09_prevent_order_exceeding_stock(self):
        self.client.login(username='apex_parts', password='Supplier@Pass123!')

        # self.part2 has stock_quantity = 4
        order = SparePartOrder.objects.create(
            customer=self.customer,
            shipping_address='99 Oak Drive',
            contact_phone='+1-555-019-3301',
            total_amount=Decimal('8500.00'),
            status=SparePartOrder.Status.PENDING
        )
        # Customer orders 10 units of an item with only 4 units in stock
        item = SparePartOrderItem.objects.create(
            order=order,
            part=self.part2,
            quantity=10,
            unit_price=self.part2.price
        )

        res = self.client.post(
            reverse('suppliers:update_order_status', args=[order.pk]),
            {'status': SparePartOrder.Status.CONFIRMED},
            follow=True
        )
        self.assertEqual(res.status_code, 200)
        order.refresh_from_db()
        # Order status MUST remain PENDING due to stock deficiency
        self.assertEqual(order.status, SparePartOrder.Status.PENDING)
        self.part2.refresh_from_db()
        self.assertEqual(self.part2.stock_quantity, 4)
        item.refresh_from_db()
        self.assertFalse(item.stock_deducted)
        self.assertContains(res, 'Insufficient stock')

    # -------------------------------------------------------------
    # Test 10: Safe Stock Integrity (Deduction on Confirm, Restoration on Cancel)
    # -------------------------------------------------------------
    def test_10_safe_stock_deduction_and_restoration(self):
        self.client.login(username='apex_parts', password='Supplier@Pass123!')

        # initial stock of self.part1 = 20
        order = SparePartOrder.objects.create(
            customer=self.customer,
            shipping_address='12 Willow Way',
            contact_phone='+1-555-019-3301',
            total_amount=Decimal('13500.00'),
            status=SparePartOrder.Status.PENDING
        )
        item = SparePartOrderItem.objects.create(
            order=order,
            part=self.part1,
            quantity=3,
            unit_price=self.part1.price,
            stock_deducted=False
        )

        # 1. Confirm Order -> Deducts 3 units
        self.client.post(
            reverse('suppliers:update_order_status', args=[order.pk]),
            {'status': SparePartOrder.Status.CONFIRMED}
        )
        self.part1.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(self.part1.stock_quantity, 17)
        self.assertTrue(item.stock_deducted)

        # 2. Advance to Processing -> Should NOT double-deduct
        self.client.post(
            reverse('suppliers:update_order_status', args=[order.pk]),
            {'status': SparePartOrder.Status.PROCESSING}
        )
        self.part1.refresh_from_db()
        self.assertEqual(self.part1.stock_quantity, 17)

        # 3. Cancel Order -> Safely restores 3 units
        self.client.post(
            reverse('suppliers:update_order_status', args=[order.pk]),
            {'status': SparePartOrder.Status.CANCELLED}
        )
        self.part1.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(self.part1.stock_quantity, 20)
        self.assertFalse(item.stock_deducted)

        order.refresh_from_db()
        self.assertEqual(order.status, SparePartOrder.Status.CANCELLED)

    # -------------------------------------------------------------
    # Test 11: Data Isolation & IDOR Protection Between Suppliers
    # -------------------------------------------------------------
    def test_11_data_isolation_and_idor(self):
        # Login as Supplier B
        self.client.login(username='metro_spares', password='SupplierB@Pass123!')

        # Supplier B attempts to edit Supplier A's part -> 404 Not Found
        res_edit = self.client.get(reverse('suppliers:product_edit', args=[self.part1.pk]))
        self.assertEqual(res_edit.status_code, 404)

        # Supplier B attempts to delete Supplier A's part -> 404 Not Found
        res_del = self.client.post(reverse('suppliers:product_delete', args=[self.part1.pk]))
        self.assertEqual(res_del.status_code, 404)

        # Supplier B attempts to access order containing only Supplier A's items -> 404 Not Found
        order_a = SparePartOrder.objects.create(
            customer=self.customer,
            shipping_address='Address A',
            contact_phone='+1-555-019-3301',
            total_amount=Decimal('4500.00'),
            status=SparePartOrder.Status.PENDING
        )
        SparePartOrderItem.objects.create(
            order=order_a,
            part=self.part1,
            quantity=1,
            unit_price=self.part1.price
        )

        res_order = self.client.get(reverse('suppliers:order_detail', args=[order_a.pk]))
        self.assertEqual(res_order.status_code, 404)

        res_update = self.client.post(
            reverse('suppliers:update_order_status', args=[order_a.pk]),
            {'status': SparePartOrder.Status.CONFIRMED}
        )
        self.assertEqual(res_update.status_code, 404)

    # -------------------------------------------------------------
    # Test 12: Blocked Unapproved Operations (Verification Gating)
    # -------------------------------------------------------------
    def test_12_blocked_unapproved_operations(self):
        # Set Supplier A to PENDING status
        self.supplier.verification_status = SupplierProfile.VerificationStatus.PENDING
        self.supplier.save()

        self.client.login(username='apex_parts', password='Supplier@Pass123!')

        # Attempt to add product while pending -> Redirect with error message
        post_data = {
            'part_name': 'Unauthorized Brake Rotor',
            'part_number': 'ROTOR-UNAUTH-01',
            'price': '3500.00',
            'stock_quantity': '10',
            'is_available': 'on'
        }
        res_add = self.client.post(reverse('suppliers:product_add'), post_data, follow=True)
        self.assertEqual(res_add.status_code, 200)
        self.assertFalse(SparePart.objects.filter(part_number='ROTOR-UNAUTH-01').exists())
        self.assertContains(res_add, 'must be approved before you can list new products')

        # Attempt to process order while pending
        order = SparePartOrder.objects.create(
            customer=self.customer,
            shipping_address='Test Destination',
            contact_phone='+1-555-019-3301',
            total_amount=Decimal('4500.00'),
            status=SparePartOrder.Status.PENDING
        )
        SparePartOrderItem.objects.create(
            order=order,
            part=self.part1,
            quantity=1,
            unit_price=self.part1.price
        )

        res_proc = self.client.post(
            reverse('suppliers:update_order_status', args=[order.pk]),
            {'status': SparePartOrder.Status.CONFIRMED},
            follow=True
        )
        self.assertEqual(res_proc.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, SparePartOrder.Status.PENDING)
        self.assertContains(res_proc, 'Supplier approval is required to process and fulfill customer orders')

    # -------------------------------------------------------------
    # Test 13: Sales and Revenue Calculations (Strictly Delivered Orders)
    # -------------------------------------------------------------
    def test_13_sales_and_revenue_calculations(self):
        self.client.login(username='apex_parts', password='Supplier@Pass123!')

        # Order 1: DELIVERED (2 brake pads @ 4500 = 9000)
        order_delivered = SparePartOrder.objects.create(
            customer=self.customer,
            shipping_address='Delivered Destination',
            contact_phone='+1-555-019-3301',
            total_amount=Decimal('9000.00'),
            status=SparePartOrder.Status.DELIVERED
        )
        SparePartOrderItem.objects.create(
            order=order_delivered,
            part=self.part1,
            quantity=2,
            unit_price=Decimal('4500.00'),
            stock_deducted=True
        )

        # Order 2: PENDING (5 oil filters @ 850 = 4250) -> MUST NOT be in revenue
        order_pending = SparePartOrder.objects.create(
            customer=self.customer,
            shipping_address='Pending Destination',
            contact_phone='+1-555-019-3301',
            total_amount=Decimal('4250.00'),
            status=SparePartOrder.Status.PENDING
        )
        SparePartOrderItem.objects.create(
            order=order_pending,
            part=self.part2,
            quantity=5,
            unit_price=Decimal('850.00'),
            stock_deducted=False
        )

        # Order 3: CANCELLED -> MUST NOT be in revenue
        order_cancelled = SparePartOrder.objects.create(
            customer=self.customer,
            shipping_address='Cancelled Destination',
            contact_phone='+1-555-019-3301',
            total_amount=Decimal('12500.00'),
            status=SparePartOrder.Status.CANCELLED
        )
        SparePartOrderItem.objects.create(
            order=order_cancelled,
            part=self.part3,
            quantity=1,
            unit_price=Decimal('12500.00'),
            stock_deducted=False
        )

        res_sales = self.client.get(reverse('suppliers:sales'))
        self.assertEqual(res_sales.status_code, 200)

        # Revenue should strictly equal 9000.00 (from order_delivered only)
        self.assertEqual(res_sales.context['total_revenue'], Decimal('9000.00'))
        # Total units sold = 2
        self.assertEqual(res_sales.context['total_units_sold'], 2)
        # Total completed orders = 1
        self.assertEqual(res_sales.context['total_completed_orders'], 1)

        # Leaderboard should have part1 with 2 units sold
        best_sellers = list(res_sales.context['best_sellers'])
        self.assertEqual(len(best_sellers), 1)
        self.assertEqual(best_sellers[0].pk, self.part1.pk)
        self.assertEqual(best_sellers[0].units_sold, 2)

    # -------------------------------------------------------------
    # Test 14: Non-Supplier Access Control and Unauthenticated Redirection
    # -------------------------------------------------------------
    def test_14_unauthorized_access_and_rbac(self):
        # 1. Unauthenticated user redirected to login
        self.client.logout()
        res_unauth = self.client.get(reverse('suppliers:dashboard'))
        self.assertEqual(res_unauth.status_code, 302)
        self.assertIn('/accounts/login/', res_unauth.url)

        # 2. Vehicle Owner user denied access (403 Forbidden)
        self.client.login(username='car_owner_lisa', password='Customer@Pass123!')
        res_owner = self.client.get(reverse('suppliers:dashboard'))
        self.assertEqual(res_owner.status_code, 403)

        # 3. Mechanic user denied access (403 Forbidden)
        self.client.login(username='sam_mechanic', password='Mechanic@Pass123!')
        res_mech = self.client.get(reverse('suppliers:dashboard'))
        self.assertEqual(res_mech.status_code, 403)
