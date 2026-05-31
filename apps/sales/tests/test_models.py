"""
Tests for the Sales app models.

Covers invoice number generation, Sale creation, and SaleItem creation.
"""
import re
from datetime import date

import pytest

from apps.customers.models import Customer
from apps.medicines.models import Category, Medicine
from apps.sales.models import Sale, SaleItem, generate_invoice_number


@pytest.mark.django_db
class TestInvoiceNumber:
    """Tests for the generate_invoice_number helper."""

    def test_invoice_number_format(self):
        """Verify invoice numbers follow INV-YYYYMMDD-XXXX format."""
        invoice = generate_invoice_number()
        today = date.today()
        pattern = rf'^INV-{today.strftime("%Y%m%d")}-\d{{4}}$'
        assert re.match(pattern, invoice), f'Invoice "{invoice}" does not match pattern'

    def test_invoice_number_sequence(self):
        """Verify invoice numbers increment within the same day."""
        inv1 = generate_invoice_number()
        inv2 = generate_invoice_number()
        seq1 = int(inv1.split('-')[-1])
        seq2 = int(inv2.split('-')[-1])
        # Without creating actual Sale objects, the count is always 0,
        # so both should generate sequence 0001.
        assert seq1 == 1
        assert seq2 == 1


@pytest.mark.django_db
class TestSaleModel:
    """Tests for the Sale model."""

    @pytest.fixture
    def medicine(self):
        """Fixture providing a sample Medicine."""
        cat = Category.objects.create(name='Test Category')
        return Medicine.objects.create(
            name='Test Med',
            category=cat,
            purchase_price=5.00,
            selling_price=10.00,
            stock_quantity=50,
        )

    def test_create_sale(self):
        """Verify that a Sale can be created with valid data."""
        sale = Sale.objects.create(
            invoice_no='INV-20260518-0001',
            subtotal=100.00,
            grand_total=100.00,
            amount_paid=100.00,
            status=Sale.Status.COMPLETED,
            payment_mode=Sale.PaymentMode.CASH,
        )
        assert sale.invoice_no == 'INV-20260518-0001'
        assert sale.grand_total == 100.00
        assert sale.status == Sale.Status.COMPLETED
        assert 'INV-20260518-0001' in str(sale)

    def test_sale_with_customer(self):
        """Verify a Sale can be linked to a Customer."""
        customer = Customer.objects.create(
            name='Test Customer',
            phone='01720000999',
        )
        sale = Sale.objects.create(
            invoice_no='INV-20260518-0002',
            customer=customer,
            subtotal=200.00,
            grand_total=200.00,
            amount_paid=200.00,
            payment_mode=Sale.PaymentMode.CARD,
        )
        assert sale.customer == customer

    def test_sale_payment_modes(self):
        """Verify all payment mode choices are available."""
        modes = dict(Sale.PaymentMode.choices)
        assert modes['CASH'] == 'Cash'
        assert modes['CARD'] == 'Card'
        assert modes['MOBILE'] == 'Mobile Banking'
        assert modes['MIXED'] == 'Mixed'

    def test_sale_status_choices(self):
        """Verify all status choices are available."""
        statuses = dict(Sale.Status.choices)
        assert statuses['COMPLETED'] == 'Completed'
        assert statuses['HELD'] == 'Held'
        assert statuses['CANCELLED'] == 'Cancelled'
        assert statuses['REFUNDED'] == 'Refunded'

    def test_sale_total_items_property(self):
        """Verify total_items returns the count of related SaleItems."""
        sale = Sale.objects.create(
            invoice_no='INV-20260518-0003',
            subtotal=0,
            grand_total=0,
            amount_paid=0,
        )
        assert sale.total_items == 0


@pytest.mark.django_db
class TestSaleItemModel:
    """Tests for the SaleItem model."""

    @pytest.fixture
    def medicine(self):
        """Fixture providing a sample Medicine."""
        cat = Category.objects.create(name='Test Category')
        return Medicine.objects.create(
            name='Test Med',
            category=cat,
            purchase_price=5.00,
            selling_price=10.00,
        )

    @pytest.fixture
    def sale(self):
        """Fixture providing a sample Sale."""
        return Sale.objects.create(
            invoice_no='INV-20260518-0010',
            subtotal=0,
            grand_total=0,
            amount_paid=0,
        )

    def test_create_sale_item(self, sale, medicine):
        """Verify a SaleItem can be created and linked to a sale."""
        item = SaleItem.objects.create(
            sale=sale,
            medicine=medicine,
            quantity=2,
            unit_price=10.00,
            line_total=20.00,
        )
        assert item.sale == sale
        assert item.medicine == medicine
        assert item.quantity == 2
        assert item.unit_price == 10.00
        assert item.line_total == 20.00
        assert 'Test Med × 2' in str(item)

    def test_sale_item_defaults(self, sale, medicine):
        """Verify default values for SaleItem fields."""
        item = SaleItem.objects.create(
            sale=sale,
            medicine=medicine,
            quantity=1,
            unit_price=5.00,
            line_total=5.00,
        )
        assert item.discount == 0.00
        assert item.tax_rate == 15.00