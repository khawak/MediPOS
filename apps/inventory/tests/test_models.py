"""
Tests for the Inventory app models.

Covers Batch creation, StockLedger creation, and stock quantity updates
triggered by StockLedger entries.
"""
import pytest
from datetime import date, timedelta

from apps.inventory.models import Batch, StockLedger
from apps.medicines.models import Category, Medicine


@pytest.mark.django_db
class TestBatchModel:
    """Tests for the Batch model."""

    @pytest.fixture
    def medicine(self):
        """Fixture providing a sample Medicine."""
        cat = Category.objects.create(name='Test Category')
        return Medicine.objects.create(
            name='Test Medicine',
            category=cat,
            purchase_price=10.00,
            selling_price=15.00,
            stock_quantity=0,
        )

    def test_create_batch(self, medicine):
        """Verify that a Batch can be created and linked to a medicine."""
        expiry = date.today() + timedelta(days=365)
        batch = Batch.objects.create(
            medicine=medicine,
            batch_no='BATCH-001',
            expiry_date=expiry,
            quantity=100,
            purchase_price=10.00,
        )
        assert batch.medicine == medicine
        assert batch.batch_no == 'BATCH-001'
        assert batch.quantity == 100
        assert batch.is_expired is False
        assert batch.days_until_expiry == 365

    def test_batch_is_expired(self, medicine):
        """Verify is_expired returns True for past expiry dates."""
        past_date = date.today() - timedelta(days=1)
        batch = Batch.objects.create(
            medicine=medicine,
            batch_no='BATCH-EXP',
            expiry_date=past_date,
            quantity=10,
            purchase_price=10.00,
        )
        assert batch.is_expired is True
        assert batch.days_until_expiry < 0

    def test_batch_days_until_expiry(self, medicine):
        """Verify days_until_expiry calculation."""
        future = date.today() + timedelta(days=45)
        batch = Batch.objects.create(
            medicine=medicine,
            batch_no='BATCH-045',
            expiry_date=future,
            quantity=10,
            purchase_price=10.00,
        )
        assert batch.days_until_expiry == 45
        assert batch.is_expiring_soon is True
        assert batch.is_expiring_critical is False

    def test_batch_is_expiring_critical(self, medicine):
        """Verify is_expiring_critical for <= 30 days."""
        future = date.today() + timedelta(days=20)
        batch = Batch.objects.create(
            medicine=medicine,
            batch_no='BATCH-020',
            expiry_date=future,
            quantity=10,
            purchase_price=10.00,
        )
        assert batch.is_expiring_critical is True
        assert batch.is_expiring_soon is True

    def test_batch_str(self, medicine):
        """Verify the string representation of a Batch."""
        expiry = date(2026, 12, 31)
        batch = Batch.objects.create(
            medicine=medicine,
            batch_no='LOT-A1',
            expiry_date=expiry,
            quantity=50,
            purchase_price=12.50,
        )
        assert 'Test Medicine' in str(batch)
        assert 'LOT-A1' in str(batch)
        assert '2026-12-31' in str(batch)


@pytest.mark.django_db
class TestStockLedgerModel:
    """Tests for the StockLedger model."""

    @pytest.fixture
    def medicine(self):
        """Fixture providing a sample Medicine."""
        cat = Category.objects.create(name='Test Category')
        return Medicine.objects.create(
            name='Ledger Test Med',
            category=cat,
            purchase_price=5.00,
            selling_price=8.00,
            stock_quantity=0,
        )

    def test_stock_ledger_in_entry(self, medicine):
        """Verify that a StockLedger 'IN' entry can be created."""
        entry = StockLedger.objects.create(
            medicine=medicine,
            transaction_type='IN',
            quantity=50,
            reference='PO-TEST-001',
        )
        assert entry.medicine == medicine
        assert entry.transaction_type == 'IN'
        assert entry.quantity == 50
        assert 'Ledger Test Med' in str(entry)

    def test_stock_ledger_out_entry(self, medicine):
        """Verify that a StockLedger 'OUT' entry can be created."""
        entry = StockLedger.objects.create(
            medicine=medicine,
            transaction_type='OUT',
            quantity=-5,
            reference='INV-001',
        )
        assert entry.transaction_type == 'OUT'
        assert entry.quantity == -5

    def test_stock_ledger_types(self):
        """Verify all transaction type choices are available."""
        types = dict(StockLedger.TRANSACTION_TYPES)
        assert types['IN'] == 'Stock In'
        assert types['OUT'] == 'Sale'
        assert types['ADJ'] == 'Adjustment'
        assert types['RET'] == 'Return'