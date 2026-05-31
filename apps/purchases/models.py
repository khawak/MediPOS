"""
MediPOS Purchases / Procurement — Models.

Defines PurchaseOrder and PurchaseOrderItem models for the pharmacy
purchasing workflow, including auto-generated PO numbers and status
tracking from DRAFT → ORDERED → RECEIVED (or CANCELLED).
"""

from datetime import date, datetime

from django.db import models, transaction
from django.urls import reverse
from django.utils.timezone import now


def generate_po_number():
    """
    Generate a unique purchase order number in the format 'PO-YYYYMMDD-XXXX'.

    XXXX is a zero-padded sequential counter that resets daily.
    Uses select_for_update() inside a transaction to prevent race
    conditions under concurrent requests.

    Returns:
        str: A PO number like 'PO-20260518-0001'.
    """
    today = date.today()
    prefix = f'PO-{today.strftime("%Y%m%d")}'

    with transaction.atomic():
        last = (
            PurchaseOrder.objects
            .filter(order_date=today)
            .select_for_update()
            .order_by('-po_number')
            .first()
        )
        if last and last.po_number:
            try:
                seq = int(last.po_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1

    return f'{prefix}-{seq:04d}'


class PurchaseOrder(models.Model):
    """
    Represents a purchase order sent to a supplier.

    Tracks the PO lifecycle: DRAFT (being prepared) → ORDERED (sent to supplier)
    → RECEIVED (stock received) or CANCELLED (voided). Items are tracked via
    the related PurchaseOrderItem model.

    When a PO is received, Batch records are created which trigger the existing
    signal chain (Batch → StockLedger IN → Medicine.stock_quantity update).

    Attributes:
        STATUS_CHOICES: Lifecycle states for a purchase order.
        po_number: Auto-generated unique PO number.
        supplier: The supplier this PO is sent to.
        order_date: Date the PO was created/sent.
        expected_delivery_date: Anticipated delivery date (optional).
        status: Current lifecycle status.
        total_amount: Computed sum of all item line totals.
        received_by: User who received/confirmed the stock.
        notes: Optional additional notes.
        created_by: User who created this PO.
        created_at: Timestamp of creation.
        updated_at: Timestamp of last update.
    """

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ORDERED', 'Ordered'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ]

    po_number = models.CharField(
        max_length=50,
        unique=True,
        help_text='Auto-generated unique purchase order number.',
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        help_text='The supplier this purchase order is sent to.',
    )
    order_date = models.DateField(
        default=now,
        help_text='Date the purchase order was created or sent.',
    )
    expected_delivery_date = models.DateField(
        blank=True,
        null=True,
        help_text='Anticipated delivery date for this order.',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        help_text='Current status of the purchase order.',
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text='Computed total of all line items.',
    )
    received_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_pos',
        help_text='User who received the stock for this PO.',
    )
    notes = models.TextField(
        blank=True,
        help_text='Optional internal notes about this purchase order.',
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_pos',
        help_text='User who created this purchase order.',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Timestamp of creation.',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Timestamp of last update.',
    )

    class Meta:
        ordering = ['-order_date']
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'

    def __str__(self):
        """Return a concise PO identifier."""
        return f'PO #{self.po_number}'

    def get_absolute_url(self):
        """Return the URL to this PO's detail view."""
        return reverse('purchases:po_detail', kwargs={'pk': self.pk})

    @property
    def items_count(self):
        """Return the number of line items in this purchase order."""
        return self.items.count()


class PurchaseOrderItem(models.Model):
    """
    Represents a single line item within a purchase order.

    Each item specifies a medicine, quantity, unit price, and optional
    batch/expiry info from the supplier. The line_total is auto-calculated
    on save, and the parent PO's total_amount is recalculated accordingly.

    Attributes:
        purchase_order: The parent purchase order.
        medicine: The medicine being ordered.
        quantity: Number of units ordered.
        unit_price: Purchase price per unit in BDT.
        batch_no: Supplier's batch/lot number (optional).
        expiry_date: Supplier's batch expiry date (optional).
        line_total: Computed total for this line (quantity × unit_price).
    """

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items',
        help_text='The parent purchase order.',
    )
    medicine = models.ForeignKey(
        'medicines.Medicine',
        on_delete=models.PROTECT,
        related_name='po_items',
        help_text='The medicine being ordered.',
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text='Number of units ordered.',
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Purchase price per unit in BDT.',
    )
    batch_no = models.CharField(
        max_length=100,
        blank=True,
        help_text="Supplier's batch or lot number.",
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text="Supplier's batch expiry date.",
    )
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Computed line total (quantity × unit_price).',
    )

    class Meta:
        verbose_name = 'Purchase Order Item'
        verbose_name_plural = 'Purchase Order Items'

    def __str__(self):
        """Return the medicine name and quantity for this line item."""
        return f'{self.medicine.name} x {self.quantity}'

    def save(self, *args, **kwargs):
        """
        Auto-calculate line_total and update the parent PO's total_amount.

        On every save, this item's line_total is recomputed as
        quantity × unit_price, and the parent PurchaseOrder's total_amount
        is recalculated as the sum of all its items' line_totals.
        """
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        # Recalculate the parent PO's total
        if self.purchase_order_id:
            po = PurchaseOrder.objects.get(pk=self.purchase_order_id)
            po.total_amount = po.items.aggregate(
                total=models.Sum('line_total')
            )['total'] or 0.00
            po.save(update_fields=['total_amount'])