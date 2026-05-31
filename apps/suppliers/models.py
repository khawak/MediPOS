"""
MediPOS Suppliers — Models.

Defines the Supplier model for managing pharmacy suppliers and vendors.
"""
from decimal import Decimal

from django.db import models
from django.urls import reverse


class Supplier(models.Model):
    """
    Represents a pharmaceutical supplier or vendor.

    Tracks company details, contact information, balance (negative = we
    owe them / dues, positive = they owe us / advance paid), and active status.
    Purchase history is linked via the purchases app (Phase 8).
    """

    name = models.CharField(max_length=200, help_text='Company or supplier name.')
    contact_person = models.CharField(
        max_length=100,
        blank=True,
        help_text='Primary contact person at this supplier.',
    )
    phone = models.CharField(max_length=20, help_text='Primary contact number.')
    email = models.EmailField(blank=True, help_text='Contact email address.')
    address = models.TextField(blank=True, help_text='Physical or mailing address.')
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=(
            'Current account balance. Negative = we owe supplier (dues), '
            'positive = advance paid to supplier.'
        ),
    )
    notes = models.TextField(
        blank=True,
        help_text='Additional notes about this supplier.',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this supplier is considered active.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'

    def __str__(self):
        """Return the supplier's name as its string representation."""
        return self.name

    def get_absolute_url(self):
        """Return the URL for this supplier's detail view."""
        return reverse('suppliers:supplier_detail', kwargs={'pk': self.pk})

    @property
    def balance_display(self):
        """Human-readable balance: 'Dues: 5000.00' or 'Advance: 2000.00' or 'Settled'."""
        if self.balance < 0:
            return f'Dues (we owe): {abs(self.balance)}'
        elif self.balance > 0:
            return f'Advance paid: {self.balance}'
        return 'Settled'