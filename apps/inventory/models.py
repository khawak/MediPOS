"""
MediPOS Inventory — Models.

Defines Batch (lot tracking with expiry) and StockLedger (audit trail)
models for the pharmacy inventory management system.
"""
from datetime import date

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Batch(models.Model):
    """
    Represents a specific batch/lot of a medicine received from a supplier.

    Each batch has its own expiry date, quantity, and purchase metadata.
    Stock movements are tracked via related StockLedger entries.

    Attributes:
        medicine: The medicine this batch belongs to.
        supplier: The supplier who provided this batch (optional).
        batch_no: Batch/lot number from the supplier.
        manufacture_date: Date the batch was manufactured (optional).
        expiry_date: Date the batch expires.
        quantity: Current quantity remaining in this batch.
        purchase_price: Per-unit purchase price for this batch.
        purchase_order: Reference PO number (will become FK in Phase 8).
        is_active: Whether this batch is still active.
        created_at: Timestamp of creation.
        updated_at: Timestamp of last update.
    """

    medicine = models.ForeignKey(
        'medicines.Medicine',
        on_delete=models.CASCADE,
        related_name='batches',
        verbose_name=_('medicine'),
        help_text=_('The medicine this batch belongs to.'),
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='batches',
        verbose_name=_('supplier'),
        help_text=_('The supplier who provided this batch.'),
    )
    batch_no = models.CharField(
        max_length=100,
        verbose_name=_('batch number'),
        help_text=_('Batch or lot number from the supplier.'),
    )
    manufacture_date = models.DateField(
        blank=True,
        null=True,
        verbose_name=_('manufacture date'),
        help_text=_('Date the batch was manufactured.'),
    )
    expiry_date = models.DateField(
        verbose_name=_('expiry date'),
        help_text=_('Date the batch expires.'),
    )
    quantity = models.PositiveIntegerField(
        default=0,
        verbose_name=_('quantity'),
        help_text=_('Current quantity remaining in this batch.'),
    )
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_('purchase price'),
        help_text=_('Per-unit purchase price for this batch in BDT.'),
    )
    purchase_order = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('purchase order'),
        help_text=_('Reference PO number.'),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('is active'),
        help_text=_('Designates whether this batch is still active.'),
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
        verbose_name = _('Batch')
        verbose_name_plural = _('Batches')
        ordering = ['expiry_date']
        indexes = [
            models.Index(fields=['medicine']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['batch_no']),
        ]

    def __str__(self):
        """Return a descriptive string: medicine name, batch number, and expiry."""
        return f'{self.medicine.name} - {self.batch_no} (Exp: {self.expiry_date})'

    def get_absolute_url(self):
        """Return the URL to this batch's detail view."""
        return reverse('inventory:batch_detail', kwargs={'pk': self.pk})

    @property
    def is_expired(self):
        """Return True if this batch has passed its expiry date."""
        return self.expiry_date < date.today()

    @property
    def days_until_expiry(self):
        """Return the number of days until this batch expires (negative if expired)."""
        return (self.expiry_date - date.today()).days

    @property
    def is_expiring_soon(self):
        """Return True if this batch expires within 60 days."""
        return 0 <= self.days_until_expiry <= 60

    @property
    def is_expiring_critical(self):
        """Return True if this batch expires within 30 days."""
        return 0 <= self.days_until_expiry <= 30


class StockLedger(models.Model):
    """
    Audit trail for ALL stock movements — stock-in, sale, adjustment, and return.

    Every change to a medicine's stock quantity is recorded here. Positive
    quantities represent stock additions (IN, Return); negative quantities
    represent stock deductions (OUT/Sale, Adjustment).

    Attributes:
        TRANSACTION_TYPES: Choices of stock movement types.
        medicine: The medicine whose stock changed.
        batch: Optional batch affected by this transaction.
        transaction_type: Type of stock movement (IN, OUT, ADJ, RET).
        quantity: Signed integer — positive for additions, negative for deductions.
        reference: Human-readable reference (invoice #, PO #, etc.).
        note: Optional additional notes.
        created_by: User who performed the transaction.
        created_at: Timestamp of the transaction.
    """

    TRANSACTION_TYPES = [
        ('IN', _('Stock In')),
        ('OUT', _('Sale')),
        ('ADJ', _('Adjustment')),
        ('RET', _('Return')),
    ]

    medicine = models.ForeignKey(
        'medicines.Medicine',
        on_delete=models.CASCADE,
        related_name='stock_ledger',
        verbose_name=_('medicine'),
        help_text=_('The medicine whose stock changed.'),
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_ledger',
        verbose_name=_('batch'),
        help_text=_('The batch affected by this transaction (if applicable).'),
    )
    transaction_type = models.CharField(
        max_length=3,
        choices=TRANSACTION_TYPES,
        verbose_name=_('transaction type'),
        help_text=_('Type of stock movement.'),
    )
    quantity = models.IntegerField(
        verbose_name=_('quantity'),
        help_text=_('Signed quantity: positive for additions, negative for deductions.'),
    )
    reference = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('reference'),
        help_text=_('Human-readable reference (e.g., invoice #, PO #).'),
    )
    note = models.TextField(
        blank=True,
        verbose_name=_('note'),
        help_text=_('Optional additional notes about this transaction.'),
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_entries',
        verbose_name=_('created by'),
        help_text=_('User who performed the transaction.'),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('created at'),
    )

    class Meta:
        verbose_name = _('Stock Ledger')
        verbose_name_plural = _('Stock Ledger')
        ordering = ['-created_at']

    def __str__(self):
        """Return a descriptive audit string."""
        return f'{self.medicine.name} - {self.get_transaction_type_display()} {abs(self.quantity)} units'