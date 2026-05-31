"""
Management command to load demo data into MediPOS.

Creates default users, categories, medicines, suppliers, and customers.
Fully idempotent — can be run multiple times without duplicating data.

Usage:
    python manage.py load_demo_data
"""
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    """
    Load idempotent demo data for MediPOS development and testing.

    Steps:
        1.  Ensure role groups exist (delegates to setup_roles).
        2.  Create 3 users (admin, pharmacist, cashier).
        3.  Create 5 medicine categories.
        4.  Create 10 medicines with realistic names and prices.
        5.  Create 2 suppliers.
        6.  Create 3 customers.
    """

    help = 'Load idempotent demo data for MediPOS development and testing.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== MediPOS Demo Data Loader ===\n'))

        with transaction.atomic():
            self._ensure_roles()
            self._create_users()
            self._create_categories()
            self._create_medicines()
            self._create_suppliers()
            self._create_customers()

        self.stdout.write(self.style.SUCCESS('\n=== Demo data loaded successfully! ==='))

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def _ensure_roles(self):
        """Ensure role groups exist by running setup_roles."""
        self.stdout.write('  Setting up role groups...')
        call_command('setup_roles', verbosity=0)
        self.stdout.write(self.style.SUCCESS('    ✓ Role groups ready.'))

    def _create_users(self):
        """Create 3 default users and assign them to correct groups."""
        from apps.accounts.models import User

        self.stdout.write('  Creating users...')

        users_data = [
            {
                'username': 'admin',
                'password': 'admin123',
                'role': User.Role.ADMIN,
                'first_name': 'System',
                'last_name': 'Admin',
                'email': 'admin@medipos.com',
                'group': 'Admin',
            },
            {
                'username': 'pharmacist',
                'password': 'pharma123',
                'role': User.Role.PHARMACIST,
                'first_name': 'Md.',
                'last_name': 'Pharmacist',
                'email': 'pharmacist@medipos.com',
                'group': 'Pharmacist',
            },
            {
                'username': 'cashier',
                'password': 'cashier123',
                'role': User.Role.CASHIER,
                'first_name': 'Front',
                'last_name': 'Cashier',
                'email': 'cashier@medipos.com',
                'group': 'Cashier',
            },
        ]

        for data in users_data:
            group_name = data.pop('group')
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults=data,
            )
            if created:
                user.set_password(data['password'])
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'    ✓ Created user: {user.username} ({user.get_role_display()})')
                )
            else:
                # Update role if needed
                updated = False
                if user.role != data['role']:
                    user.role = data['role']
                    updated = True
                if not user.check_password(data['password']):
                    user.set_password(data['password'])
                    updated = True
                if updated:
                    user.save()
                self.stdout.write(
                    self.style.WARNING(f'    ⚠ User already exists: {user.username} (updated)')
                )

            # Assign to correct group
            try:
                group = Group.objects.get(name=group_name)
                user.groups.add(group)
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.NOTICE(f'      Group "{group_name}" not found, skipping.')
                )

    def _create_categories(self):
        """Create 5 default medicine categories."""
        from apps.medicines.models import Category

        self.stdout.write('  Creating categories...')

        categories = [
            {'name': 'Antibiotics', 'description': 'Antibacterial and antimicrobial medications.'},
            {'name': 'Pain Relief', 'description': 'Analgesics and pain management drugs.'},
            {'name': 'Diabetes Care', 'description': 'Insulin and oral hypoglycemic agents.'},
            {'name': 'Vitamins & Supplements', 'description': 'Dietary supplements and multivitamins.'},
            {'name': 'First Aid', 'description': 'Bandages, antiseptics, and emergency supplies.'},
        ]

        for cat_data in categories:
            cat, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'    ✓ Created category: {cat.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'    ⚠ Category already exists: {cat.name}'))

    def _create_medicines(self):
        """Create 10 medicines with realistic names and prices."""
        from apps.medicines.models import Category, Medicine

        self.stdout.write('  Creating medicines...')

        medicines_data = [
            {
                'name': 'Amoxicillin 500mg',
                'generic_name': 'Amoxicillin',
                'brand': 'Square Pharma',
                'category_name': 'Antibiotics',
                'unit': 'Pcs',
                'purchase_price': 6.00,
                'selling_price': 8.00,
                'stock_quantity': 200,
                'reorder_level': 20,
            },
            {
                'name': 'Ciprofloxacin 500mg',
                'generic_name': 'Ciprofloxacin',
                'brand': 'Beximco',
                'category_name': 'Antibiotics',
                'unit': 'Pcs',
                'purchase_price': 10.00,
                'selling_price': 13.00,
                'stock_quantity': 150,
                'reorder_level': 15,
            },
            {
                'name': 'Napa 500mg',
                'generic_name': 'Paracetamol',
                'brand': 'Beximco',
                'category_name': 'Pain Relief',
                'unit': 'Pcs',
                'purchase_price': 0.80,
                'selling_price': 1.20,
                'stock_quantity': 500,
                'reorder_level': 50,
            },
            {
                'name': 'Napa Extra',
                'generic_name': 'Paracetamol + Caffeine',
                'brand': 'Beximco',
                'category_name': 'Pain Relief',
                'unit': 'Pcs',
                'purchase_price': 2.50,
                'selling_price': 3.50,
                'stock_quantity': 300,
                'reorder_level': 30,
            },
            {
                'name': 'Ibuprofen 400mg',
                'generic_name': 'Ibuprofen',
                'brand': 'ACI',
                'category_name': 'Pain Relief',
                'unit': 'Pcs',
                'purchase_price': 5.00,
                'selling_price': 7.00,
                'stock_quantity': 250,
                'reorder_level': 25,
            },
            {
                'name': 'Metformin 850mg',
                'generic_name': 'Metformin Hydrochloride',
                'brand': 'Square Pharma',
                'category_name': 'Diabetes Care',
                'unit': 'Pcs',
                'purchase_price': 3.00,
                'selling_price': 4.50,
                'stock_quantity': 180,
                'reorder_level': 20,
            },
            {
                'name': 'Glimepiride 2mg',
                'generic_name': 'Glimepiride',
                'brand': 'Incepta',
                'category_name': 'Diabetes Care',
                'unit': 'Pcs',
                'purchase_price': 4.00,
                'selling_price': 6.00,
                'stock_quantity': 120,
                'reorder_level': 15,
            },
            {
                'name': 'Oravit Multi',
                'generic_name': 'Multivitamin + Minerals',
                'brand': 'Square Pharma',
                'category_name': 'Vitamins & Supplements',
                'unit': 'Pcs',
                'purchase_price': 3.50,
                'selling_price': 5.00,
                'stock_quantity': 100,
                'reorder_level': 10,
            },
            {
                'name': 'Calbo-D',
                'generic_name': 'Calcium + Vitamin D3',
                'brand': 'Beximco',
                'category_name': 'Vitamins & Supplements',
                'unit': 'Pcs',
                'purchase_price': 8.00,
                'selling_price': 12.00,
                'stock_quantity': 80,
                'reorder_level': 10,
            },
            {
                'name': 'Savlon Antiseptic',
                'generic_name': 'Cetrimide + Chlorhexidine',
                'brand': 'ACI',
                'category_name': 'First Aid',
                'unit': 'Bottle',
                'purchase_price': 55.00,
                'selling_price': 75.00,
                'stock_quantity': 40,
                'reorder_level': 5,
            },
        ]

        for med_data in medicines_data:
            category_name = med_data.pop('category_name')
            try:
                category = Category.objects.get(name=category_name)
            except Category.DoesNotExist:
                self.stdout.write(
                    self.style.NOTICE(f'      Category "{category_name}" not found, skipping {med_data["name"]}.')
                )
                continue

            medicine, created = Medicine.objects.get_or_create(
                name=med_data['name'],
                defaults={**med_data, 'category': category},
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'    ✓ Created medicine: {medicine.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'    ⚠ Medicine already exists: {medicine.name}')
                )

    def _create_suppliers(self):
        """Create 2 default suppliers."""
        from apps.suppliers.models import Supplier

        self.stdout.write('  Creating suppliers...')

        suppliers_data = [
            {
                'name': 'Square Pharmaceuticals Ltd.',
                'contact_person': 'Mr. Rahman',
                'phone': '01710000001',
                'email': 'sales@squarepharma.com',
                'address': 'Square Centre, 48 Mohakhali C/A, Dhaka-1212',
            },
            {
                'name': 'Beximco Pharmaceuticals Ltd.',
                'contact_person': 'Mr. Hossain',
                'phone': '01710000002',
                'email': 'info@beximcopharma.com',
                'address': '19 Dhanmondi R/A, Road No. 7, Dhaka-1205',
            },
        ]

        for sup_data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                name=sup_data['name'],
                defaults=sup_data,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'    ✓ Created supplier: {supplier.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'    ⚠ Supplier already exists: {supplier.name}'))

    def _create_customers(self):
        """Create 3 default customers."""
        from apps.customers.models import Customer

        self.stdout.write('  Creating customers...')

        customers_data = [
            {
                'name': 'Mr. Karim Ahmed',
                'phone': '01720000001',
                'email': 'karim@example.com',
                'address': 'House 12, Road 5, Gulshan-1, Dhaka',
            },
            {
                'name': 'Mrs. Fatema Begum',
                'phone': '01720000002',
                'email': 'fatema@example.com',
                'address': 'Flat 3B, Block C, Banani, Dhaka',
            },
            {
                'name': 'Rafiq Hasan',
                'phone': '01720000003',
                'email': '',
                'address': '45/A, Old Dhaka, Chawkbazar',
            },
        ]

        for cust_data in customers_data:
            customer, created = Customer.objects.get_or_create(
                phone=cust_data['phone'],
                defaults=cust_data,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'    ✓ Created customer: {customer.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'    ⚠ Customer already exists: {customer.name}'))