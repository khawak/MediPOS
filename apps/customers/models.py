"""
MediPOS Customers — Models.

Defines the Customer model for managing pharmacy customers
and their loyalty points.
"""
from decimal import Decimal

from django.db import models
from django.urls import reverse


class Customer(models.Model):
    """
    Represents a pharmacy customer / patient.

    Tracks contact details, loyalty points, balance (positive = advance,
    negative = dues), and purchase history.
    Purchase history is linked via the sales app (Phase 7).
    """

    name = models.CharField(max_length=200, help_text='Full name of the customer.')
    phone = models.CharField(
        max_length=20,
        unique=True,
        help_text='Primary contact number — used as unique identifier.',
    )
    email = models.EmailField(blank=True, help_text='Email address (optional).')
    address = models.TextField(blank=True, help_text='Physical or mailing address.')
    loyalty_points = models.PositiveIntegerField(
        default=0,
        help_text='Accumulated loyalty points (1 point = 1 BDT).',
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=(
            'Current account balance. Positive = advance (customer has credit), '
            'negative = dues (customer owes).'
        ),
    )
    notes = models.TextField(blank=True, help_text='Additional notes about this customer.')
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this customer is considered active.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'

    def __str__(self):
        """Return the customer's name and phone as its string representation."""
        return f'{self.name} ({self.phone})'

    def get_absolute_url(self):
        """Return the URL for this customer's detail view."""
        return reverse('customers:customer_detail', kwargs={'pk': self.pk})

    @property
    def total_purchases(self):
        """
        Return the total number of completed purchases made by this customer.
        """
        from apps.sales.models import Sale
        return Sale.objects.filter(
            customer=self,
            status='COMPLETED',
        ).count()

    @property
    def loyalty_value(self):
        """
        Return the monetary value of the customer's loyalty points.

        Currently 1 point = 1 BDT. Configurable multiplier in future.
        """
        return self.loyalty_points

    @property
    def balance_display(self):
        """Human-readable balance: 'Advance: 500.00' or 'Dues: 300.00' or 'Settled'."""
        if self.balance > 0:
            return f'Advance: {self.balance}'
        elif self.balance < 0:
            return f'Dues: {abs(self.balance)}'
        return 'Settled'