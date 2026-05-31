"""
Tests for the Customers app models.

Covers Customer creation and loyalty_points default.
"""
import pytest
from django.db import IntegrityError

from apps.customers.models import Customer


@pytest.mark.django_db
class TestCustomerModel:
    """Tests for the Customer model."""

    def test_create_customer(self):
        """Verify that a Customer can be created with valid data."""
        customer = Customer.objects.create(
            name='Mr. Karim Ahmed',
            phone='01720000001',
            email='karim@example.com',
            address='House 12, Gulshan, Dhaka',
        )
        assert customer.name == 'Mr. Karim Ahmed'
        assert customer.phone == '01720000001'
        assert customer.email == 'karim@example.com'
        assert customer.loyalty_points == 0
        assert customer.is_active is True

    def test_customer_loyalty_points_default(self):
        """Verify loyalty_points defaults to 0."""
        customer = Customer.objects.create(
            name='Test Customer',
            phone='01720000999',
        )
        assert customer.loyalty_points == 0

    def test_customer_phone_unique(self):
        """Verify duplicate phone numbers raise IntegrityError."""
        Customer.objects.create(name='First', phone='01720000055')
        with pytest.raises(IntegrityError):
            Customer.objects.create(name='Second', phone='01720000055')

    def test_customer_str(self):
        """Verify the string representation includes name and phone."""
        customer = Customer.objects.create(
            name='Rahim Uddin',
            phone='01720000123',
        )
        expected = 'Rahim Uddin (01720000123)'
        assert str(customer) == expected

    def test_customer_loyalty_value_property(self):
        """Verify loyalty_value returns the same as loyalty_points."""
        customer = Customer.objects.create(
            name='Loyal Customer',
            phone='01720000888',
            loyalty_points=150,
        )
        assert customer.loyalty_value == 150

    def test_customer_inactive(self):
        """Verify a customer can be marked inactive."""
        customer = Customer.objects.create(
            name='Inactive Customer',
            phone='01720000777',
            is_active=False,
        )
        assert customer.is_active is False