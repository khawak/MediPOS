"""
MediPOS Payments — Models.

Defines PaymentTransaction for tracking dues payments and advances
for both Customers and Suppliers via GenericForeignKey, and
DueSettlement for linking payments to specific invoices/POs.
"""
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class PaymentTransaction(models.Model):
    """
    Records a payment or advance transaction for a Customer or Supplier.

    Uses GenericForeignKey to support both Customer and Supplier entities.
    Positive amount = receiving payment (reduces dues / increases advance).
    The balance on the target entity is updated automatically via save().

    Attributes:
        content_type: The ContentType of the payee (Customer or Supplier).
        object_id: The primary key of the payee.
        payee: GenericForeignKey to the actual Customer or Supplier instance.
        amount: Positive = payment received.
        transaction_type: Payment direction — ADVANCE or PAYMENT.
        payment_method: CASH, BANK_TRANSFER, or MOBILE_BANKING.
        reference: Optional reference number or description.
        note: Additional notes about this transaction.
        transaction_date: Date the transaction occurred (allows backdating).
        sale: Optional link to a Sale invoice (for customer due settlement).
        purchase_order: Optional link to a PurchaseOrder (for supplier due settlement).
        created_by: The user who recorded this transaction.
        created_at: Timestamp of the transaction.
    """

    ADVANCE = 'ADVANCE'
    PAYMENT = 'PAYMENT'
    TRANSACTION_TYPES = [
        (ADVANCE, _('Advance / Credit')),
        (PAYMENT, _('Payment Received')),
    ]

    CASH = 'CASH'
    BANK_TRANSFER = 'BANK'
    MOBILE_BANKING = 'MOBILE'
    PAYMENT_METHODS = [
        (CASH, _('Cash')),
        (BANK_TRANSFER, _('Bank Transfer')),
        (MOBILE_BANKING, _('Mobile Banking')),
    ]

    # Generic foreign key to Customer or Supplier
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(
            app_label='customers', model='customer'
        ) | models.Q(
            app_label='suppliers', model='supplier'
        ),
        verbose_name=_('payee type'),
    )
    object_id = models.PositiveIntegerField(verbose_name=_('payee ID'))
    payee = GenericForeignKey('content_type', 'object_id')

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('amount'),
        help_text=_('Payment amount.'),
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES,
        default=PAYMENT,
        verbose_name=_('transaction type'),
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHODS,
        default=CASH,
        verbose_name=_('payment method'),
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('reference'),
        help_text=_('Cheque number, transaction ID, or reference.'),
    )
    note = models.TextField(
        blank=True,
        verbose_name=_('note'),
        help_text=_('Additional notes about this transaction.'),
    )
    transaction_date = models.DateField(
        default=date.today,
        verbose_name=_('transaction date'),
        help_text=_('Date the transaction occurred.'),
    )
    # Optional links to specific invoices / purchase orders being settled
    sale = models.ForeignKey(
        'sales.Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_transactions',
        verbose_name=_('sale invoice'),
        help_text=_('The sale invoice this payment settles (for customer dues).'),
    )
    purchase_order = models.ForeignKey(
        'purchases.PurchaseOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_transactions',
        verbose_name=_('purchase order'),
        help_text=_('The purchase order this payment settles (for supplier dues).'),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payment_transactions',
        verbose_name=_('created by'),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('created at'),
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['transaction_date']),
        ]
        verbose_name = _('Payment Transaction')
        verbose_name_plural = _('Payment Transactions')

    def __str__(self):
        """Return a descriptive string for this transaction."""
        entity = str(self.payee) if self.payee else 'Unknown'
        return (
            f'{self.get_transaction_type_display()} — '
            f'{entity} — '
            f'৳{self.amount}'
        )

    def save(self, *args, **kwargs):
        """
        Update the payee's balance on save.

        Both ADVANCE and PAYMENT add the amount to the existing balance.
        A negative balance means dues are owed; positive means advance/credit.
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and self.payee:
            self.payee.balance += self.amount
            self.payee.save(update_fields=['balance', 'updated_at'])

    def delete(self, *args, **kwargs):
        """Reverse the payee balance effect before deleting the transaction."""
        if self.payee:
            self.payee.balance -= self.amount
            self.payee.save(update_fields=['balance', 'updated_at'])
        super().delete(*args, **kwargs)

    def get_absolute_url(self):
        """Return to the payee's detail page or payment list."""
        if self.payee:
            return self.payee.get_absolute_url()
        return reverse('payments:payment_list')

    @property
    def payee_name(self):
        """Return the name of the payee."""
        if hasattr(self, '_cached_payee'):
            return str(self._cached_payee) if self._cached_payee else ''
        return str(self.payee) if self.payee else ''

    @property
    def payee_type_name(self):
        """Return 'Customer' or 'Supplier'."""
        if self.content_type and self.content_type.model == 'customer':
            return 'Customer'
        if self.content_type and self.content_type.model == 'supplier':
            return 'Supplier'
        return ''

    @property
    def is_customer_payment(self):
        """Return True if this payment is for a customer."""
        return self.content_type and self.content_type.model == 'customer'

    @property
    def is_supplier_payment(self):
        """Return True if this payment is for a supplier."""
        return self.content_type and self.content_type.model == 'supplier'


class DueSettlement(models.Model):
    """
    Links a PaymentTransaction to a specific invoice or purchase order
    being settled, tracking how much of each due was paid off.

    This enables partial settlements — a single payment can be split
    across multiple invoices, or a single invoice can be settled by
    multiple payments.

    Attributes:
        payment: The parent PaymentTransaction.
        sale: Optional sale invoice being settled (for customer dues).
        purchase_order: Optional purchase order being settled (for supplier dues).
        amount_settled: How much of this due was settled in this payment.
        created_at: Timestamp.
    """

    payment = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.CASCADE,
        related_name='settlements',
        verbose_name=_('payment'),
    )
    sale = models.ForeignKey(
        'sales.Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='due_settlements',
        verbose_name=_('sale invoice'),
    )
    purchase_order = models.ForeignKey(
        'purchases.PurchaseOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='due_settlements',
        verbose_name=_('purchase order'),
    )
    amount_settled = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('amount settled'),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('created at'),
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Due Settlement')
        verbose_name_plural = _('Due Settlements')
        indexes = [
            models.Index(fields=['sale']),
            models.Index(fields=['purchase_order']),
        ]

    def clean(self):
        """Ensure at least one of sale or purchase_order is linked."""
        from django.core.exceptions import ValidationError
        if not self.sale and not self.purchase_order:
            raise ValidationError(
                _('DueSettlement must be linked to either a Sale or a Purchase Order.')
            )
        super().clean()

    def __str__(self):
        target = ''
        if self.sale:
            target = f'Invoice {self.sale.invoice_no}'
        elif self.purchase_order:
            target = f'PO {self.purchase_order.po_number}'
        return f'Settled ৳{self.amount_settled} for {target}'