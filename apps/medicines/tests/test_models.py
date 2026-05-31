"""
Tests for the Medicines app models.

Covers Category creation, slug auto-generation, Medicine creation,
low_stock property, and profit_margin property.
"""
import pytest
from django.db import IntegrityError

from apps.medicines.models import Category, Medicine


@pytest.mark.django_db
class TestCategoryModel:
    """Tests for the Category model."""

    def test_create_category(self):
        """Verify that a Category can be created with valid data."""
        cat = Category.objects.create(name='Pain Relief')
        assert cat.name == 'Pain Relief'
        assert cat.slug == 'pain-relief'
        assert cat.is_active is True
        assert str(cat) == 'Pain Relief'

    def test_category_slug_auto_generated(self):
        """Verify that slug is auto-generated from name on creation."""
        cat = Category.objects.create(name='Diabetes Care')
        assert cat.slug == 'diabetes-care'

    def test_category_slug_updates_on_name_change(self):
        """Verify that slug updates when name is changed."""
        cat = Category.objects.create(name='Old Name')
        assert cat.slug == 'old-name'
        cat.name = 'New Name'
        cat.save()
        cat.refresh_from_db()
        assert cat.slug == 'new-name'

    def test_category_name_unique(self):
        """Verify that duplicate category names raise IntegrityError."""
        Category.objects.create(name='Unique')
        with pytest.raises(IntegrityError):
            Category.objects.create(name='Unique')

    def test_category_inactive_filtering(self):
        """Verify inactive categories can be created."""
        cat = Category.objects.create(name='Inactive', is_active=False)
        active = Category.objects.filter(is_active=True)
        assert cat not in active


@pytest.mark.django_db
class TestMedicineModel:
    """Tests for the Medicine model."""

    @pytest.fixture
    def category(self):
        """Fixture providing a sample Category."""
        return Category.objects.create(name='Antibiotics')

    def test_create_medicine(self, category):
        """Verify that a Medicine can be created with valid data."""
        med = Medicine.objects.create(
            name='Amoxicillin 500mg',
            generic_name='Amoxicillin',
            brand='Square Pharma',
            category=category,
            purchase_price=6.00,
            selling_price=8.00,
            stock_quantity=100,
            reorder_level=10,
        )
        assert med.name == 'Amoxicillin 500mg'
        assert med.category == category
        assert str(med) == 'Amoxicillin 500mg (Square Pharma)'

    def test_medicine_str_without_brand(self, category):
        """Verify string repr without brand shows just the name."""
        med = Medicine.objects.create(
            name='Paracetamol',
            category=category,
            purchase_price=1.00,
            selling_price=2.00,
        )
        assert str(med) == 'Paracetamol'

    def test_low_stock_property(self, category):
        """Verify is_low_stock returns True when stock <= reorder_level."""
        med = Medicine.objects.create(
            name='Test Med',
            category=category,
            purchase_price=5.00,
            selling_price=10.00,
            stock_quantity=5,
            reorder_level=10,
        )
        assert med.is_low_stock is True

        med.stock_quantity = 15
        med.save()
        med.refresh_from_db()
        assert med.is_low_stock is False

        # At exact reorder level
        med.stock_quantity = 10
        med.save()
        med.refresh_from_db()
        assert med.is_low_stock is True

    def test_profit_margin_property(self, category):
        """Verify profit_margin returns selling_price - purchase_price."""
        med = Medicine.objects.create(
            name='Profit Test',
            category=category,
            purchase_price=6.00,
            selling_price=10.00,
        )
        assert med.profit_margin == 4.00