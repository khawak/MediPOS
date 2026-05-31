"""
MediPOS Returns & Refunds — Models.

Defines SalesReturn and SalesReturnItem models for the sales return
and refund workflow, including automatic restock via StockLedger entries.
"""
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class SalesReturn(models.Model):
    """
    Records a sales return / refund transaction.

    Links to the original Sale, captures the reason for return, the
    total refund amount calculated from returned items, and the user
    who processed the return.

    Attributes:
        sale: The original sale being returned (PROTECT to prevent
              deletion of sales with returns).
        return_date: Timestamp when the return was processed.
        refund_amount: Total monetary amount refunded to the customer.
        reason: Required reason explaining why the return occurred.
        processed_by: The staff member who processed this return.
        notes: Optional additional notes.
        created_at: Timestamp of record creation.
        updated_at: Timestamp of last modification.
    """

    sale = models.ForeignKey(
        'sales.Sale',
        on_delete=models.PROTECT,
        related_name='returns',
        verbose_name=_('sale'),
        help_text=_('The original sale being returned.'),
    )
    return_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('return date'),
        help_text=_('Date and time when the return was processed.'),
    )
    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_('refund amount'),
        help_text=_('Total monetary amount refunded to the customer.'),
    )
    reason = models.TextField(
        verbose_name=_('reason'),
        help_text=_('Reason for the return / refund.'),
    )
    processed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='processed_returns',
        verbose_name=_('processed by'),
        help_text=_('The staff member who processed this return.'),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('notes'),
        help_text=_('Optional additional notes about this return.'),
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
        verbose_name = _('Sales Return')
        verbose_name_plural = _('Sales Returns')
        ordering = ['-return_date']

    def __str__(self):
        """Return a string identifying this return by its sale invoice."""
        return f'Return for {self.sale.invoice_no}'

    def get_absolute_url(self):
        """Return the URL to this return's detail view."""
        return reverse('returns:sales_return_detail', kwargs={'pk': self.pk})


class SalesReturnItem(models.Model):
    """
    Individual line item within a sales return transaction.

    Each SalesReturnItem links a specific sale item to a return,
    recording the quantity returned, the unit price from the original
    sale, and the computed line total.

    Attributes:
        sales_return: The parent sales return transaction.
        sale_item: The original sale line item being returned (PROTECT).
        quantity: Number of units being returned.
        unit_price: Unit price from the original sale.
        line_total: Computed total (quantity × unit_price).
    """

    sales_return = models.ForeignKey(
        SalesReturn,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('sales return'),
        help_text=_('The parent sales return transaction.'),
    )
    sale_item = models.ForeignKey(
        'sales.SaleItem',
        on_delete=models.PROTECT,
        related_name='return_items',
        verbose_name=_('sale item'),
        help_text=_('The original sale line item being returned.'),
    )
    quantity = models.PositiveIntegerField(
        verbose_name=_('quantity'),
        help_text=_('Number of units being returned.'),
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('unit price'),
        help_text=_('Unit price from the original sale.'),
    )
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('line total'),
        help_text=_('Computed total: quantity × unit_price.'),
    )

    class Meta:
        verbose_name = _('Sales Return Item')
        verbose_name_plural = _('Sales Return Items')

    def __str__(self):
        """Return a description of the returned item."""
        return f'{self.sale_item.medicine.name} x {self.quantity}'

    def save(self, *args, **kwargs):
        """
        Override save to auto-calculate line_total from quantity and unit_price.

        Args:
            *args: Positional arguments passed to the parent save().
            **kwargs: Keyword arguments passed to the parent save().
        """
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)