"""
MediPOS Sales — Models.

Defines Sale and SaleItem models for the point-of-sale billing system.
Includes the generate_invoice_number() helper for auto-generated invoice IDs.
"""
from datetime import date
from decimal import Decimal

from django.db import models, transaction
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


def generate_invoice_number():
    """
    Generate a unique invoice number in the format INV-YYYYMMDD-XXXX.

    The XXXX suffix is a zero-padded sequential counter that resets daily.
    Uses select_for_update() inside a transaction to prevent race
    conditions under concurrent requests.

    Example: INV-20260518-0001

    Returns:
        str: A formatted invoice number string.
    """
    today = date.today()
    prefix = today.strftime('INV-%Y%m%d-')

    with transaction.atomic():
        last = (
            Sale.objects
            .filter(sale_date__date=today)
            .select_for_update()
            .order_by('-invoice_no')
            .first()
        )
        if last and last.invoice_no:
            try:
                seq = int(last.invoice_no.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1

    return f'{prefix}{seq:04d}'


class Sale(models.Model):
    """
    Represents a complete sale transaction / invoice.

    Tracks the customer, cashier, all monetary totals, payment details,
    and the current status of the transaction.

    Attributes:
        invoice_no: Unique auto-generated invoice number (e.g., INV-20260518-0001).
        customer: Optional customer associated with the sale.
        cashier: The user who processed the sale.
        sale_date: Timestamp when the sale was created.
        subtotal: Sum of all line totals before discount and tax.
        discount_amount: Flat discount amount applied.
        discount_percent: Percentage-based discount applied.
        tax_amount: Total VAT/tax across all items.
        grand_total: Final amount payable after discount and tax.
        payment_mode: Method of payment (CASH, CARD, MOBILE, MIXED).
        amount_paid: Actual amount received from the customer.
        change_amount: Change returned to the customer.
        status: Current state of the sale (COMPLETED, HELD, CANCELLED, REFUNDED).
        notes: Optional internal notes about this transaction.
        created_at: Timestamp of database record creation.
        updated_at: Timestamp of last modification.
    """

    class PaymentMode(models.TextChoices):
        """Available payment methods for a sale."""
        CASH = 'CASH', _('Cash')
        CARD = 'CARD', _('Card')
        MOBILE = 'MOBILE', _('Mobile Banking')
        MIXED = 'MIXED', _('Mixed')

    class Status(models.TextChoices):
        """Possible states for a sale transaction."""
        COMPLETED = 'COMPLETED', _('Completed')
        HELD = 'HELD', _('Held')
        CANCELLED = 'CANCELLED', _('Cancelled')
        REFUNDED = 'REFUNDED', _('Refunded')

    invoice_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('invoice number'),
        help_text=_('Unique auto-generated invoice number.'),
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name=_('customer'),
        help_text=_('The customer for this sale (optional).'),
    )
    cashier = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='sales',
        verbose_name=_('cashier'),
        help_text=_('The staff member who processed this sale.'),
    )
    sale_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('sale date'),
        help_text=_('Date and time when the sale was created.'),
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_('subtotal'),
        help_text=_('Sum of all line totals before discount.'),
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_('discount amount'),
        help_text=_('Flat discount amount applied to the sale.'),
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name=_('discount percent'),
        help_text=_('Percentage-based discount applied to the sale.'),
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_('tax amount'),
        help_text=_('Total VAT/tax across all items.'),
    )
    grand_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_('grand total'),
        help_text=_('Final amount payable after discount and tax.'),
    )
    payment_mode = models.CharField(
        max_length=20,
        choices=PaymentMode.choices,
        default=PaymentMode.CASH,
        verbose_name=_('payment mode'),
        help_text=_('Method of payment used.'),
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_('amount paid'),
        help_text=_('Actual amount received from the customer.'),
    )
    change_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_('change amount'),
        help_text=_('Change returned to the customer.'),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.COMPLETED,
        verbose_name=_('status'),
        help_text=_('Current state of the sale transaction.'),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('notes'),
        help_text=_('Optional internal notes about this transaction.'),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('created at'),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('updated at'),
    )

    class Meta:
        verbose_name = _('Sale')
        verbose_name_plural = _('Sales')
        ordering = ['-sale_date']
        indexes = [
            models.Index(fields=['invoice_no']),
            models.Index(fields=['sale_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        """Return the invoice number as the string representation."""
        return f'Invoice {self.invoice_no}'

    def get_absolute_url(self):
        """Return the URL to this sale's detail view."""
        return reverse('sales:sale_detail', kwargs={'pk': self.pk})

    @property
    def due_amount(self):
        """Return the unpaid amount (dues) for this sale."""
        due = self.grand_total - self.amount_paid
        return max(due, Decimal('0.00'))

    @property
    def total_items(self):
        """Return the total number of line items in this sale."""
        if hasattr(self, '_prefetched_objects_cache') and 'items' in self._prefetched_objects_cache:
            return len(self._prefetched_objects_cache['items'])
        return self.items.count()

    @property
    def total_quantity(self):
        """Return the sum of all item quantities in this sale."""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0


class SaleItem(models.Model):
    """
    Individual line item within a sale transaction.

    Each SaleItem links a medicine to a sale, recording the quantity sold,
    the unit price at the time of sale, any per-item discount, the applied
    tax rate, and the computed line total.

    Attributes:
        sale: The parent sale transaction.
        medicine: The medicine being sold.
        batch: Optional batch from which stock was deducted.
        quantity: Number of units sold.
        unit_price: Selling price per unit at the time of sale.
        discount: Per-item flat discount amount.
        tax_rate: Tax percentage applied at the time of sale.
        line_total: Computed total: (unit_price * quantity) - discount + tax.
    """

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('sale'),
        help_text=_('The parent sale transaction.'),
    )
    medicine = models.ForeignKey(
        'medicines.Medicine',
        on_delete=models.PROTECT,
        related_name='sale_items',
        verbose_name=_('medicine'),
        help_text=_('The medicine being sold.'),
    )
    batch = models.ForeignKey(
        'inventory.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sale_items',
        verbose_name=_('batch'),
        help_text=_('The batch from which stock was deducted.'),
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_('quantity'),
        help_text=_('Number of units sold.'),
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('unit price'),
        help_text=_('Selling price per unit at the time of sale.'),
    )
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_('discount'),
        help_text=_('Per-item flat discount amount.'),
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15.00,
        verbose_name=_('tax rate'),
        help_text=_('Tax percentage applied at the time of sale.'),
    )
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('line total'),
        help_text=_('Computed total: (unit_price × quantity) − discount + tax.'),
    )

    class Meta:
        verbose_name = _('Sale Item')
        verbose_name_plural = _('Sale Items')

    def __str__(self):
        """Return a description of the line item: medicine name × quantity."""
        return f'{self.medicine.name} × {self.quantity}'