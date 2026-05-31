"""
MediPOS Returns & Refunds — Forms.

Defines forms for the sales return workflow: invoice lookup and
return item selection with quantity validation.
"""
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.sales.models import Sale, SaleItem


class SalesReturnForm(forms.Form):
    """
    Form for looking up a sale by invoice number before processing a return.

    Validates that the sale exists, is in COMPLETED status, and hasn't
    already been fully returned.

    Fields:
        invoice_no: The invoice number to look up.
    """

    invoice_no = forms.CharField(
        max_length=50,
        label=_('Invoice Number'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('e.g., INV-20260518-0001'),
            'autofocus': 'autofocus',
        }),
        help_text=_('Enter the invoice number of the sale to return.'),
    )

    def clean_invoice_no(self):
        """
        Validate that the invoice corresponds to a returnable sale.

        Checks:
            1. The sale exists.
            2. The sale status is COMPLETED or REFUNDED (partial).
            3. The sale is not CANCELLED or HELD.

        Returns:
            The validated Sale instance.

        Raises:
            ValidationError: If the sale is invalid for return.
        """
        invoice_no = self.cleaned_data['invoice_no'].strip()

        try:
            sale = Sale.objects.get(invoice_no=invoice_no)
        except Sale.DoesNotExist:
            raise ValidationError(
                _('No sale found with invoice number "%(invoice)s".')
                % {'invoice': invoice_no}
            )

        if sale.status == Sale.Status.CANCELLED:
            raise ValidationError(
                _('Sale %(invoice)s has been cancelled and cannot be returned.')
                % {'invoice': invoice_no}
            )

        if sale.status == Sale.Status.HELD:
            raise ValidationError(
                _('Sale %(invoice)s is held and has not been completed.')
                % {'invoice': invoice_no}
            )

        # Store the resolved sale for later use
        self.sale = sale
        return invoice_no


class ReturnItemsForm(forms.Form):
    """
    Dynamically-built form for selecting which items to return and how many.

    This form expects to be initialized with a `sale` keyword argument
    that provides the SaleItems to display. Each item gets a checkbox
    and a quantity input field.

    Usage:
        form = ReturnItemsForm(sale=some_sale, data=request.POST or None)
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the form, building dynamic fields from sale items.

        For each SaleItem in the sale, creates:
            - return_{item_id}: BooleanField checkbox to select the item.
            - return_qty_{item_id}: IntegerField for the return quantity.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments — expects 'sale' (Sale instance).
        """
        self.sale = kwargs.pop('sale', None)
        super().__init__(*args, **kwargs)

        if self.sale:
            self.sale_items = self.sale.items.select_related('medicine', 'batch').all()
            for item in self.sale_items:
                # Track already-returned quantities
                already_returned = item.return_items.aggregate(
                    total=models.Sum('quantity')
                )['total'] or 0
                max_returnable = item.quantity - already_returned

                if max_returnable > 0:
                    field_name_qty = f'return_qty_{item.pk}'
                    field_name_sel = f'return_{item.pk}'

                    self.fields[field_name_sel] = forms.BooleanField(
                        required=False,
                        label=str(item),
                        widget=forms.CheckboxInput(attrs={
                            'class': 'form-check-input return-checkbox',
                            'data-item-id': item.pk,
                            'data-price': str(item.unit_price),
                        }),
                    )
                    self.fields[field_name_qty] = forms.IntegerField(
                        required=False,
                        min_value=1,
                        max_value=max_returnable,
                        initial=max_returnable,
                        label=_('Qty'),
                        widget=forms.NumberInput(attrs={
                            'class': 'form-control form-control-sm return-qty',
                            'style': 'width: 80px;',
                            'data-item-id': item.pk,
                            'data-max': max_returnable,
                        }),
                    )

    def clean(self):
        """
        Validate that at least one item is selected for return.

        Returns:
            dict: Cleaned form data.

        Raises:
            ValidationError: If no items are selected.
        """
        cleaned_data = super().clean()

        selected_items = []
        for item in self.sale_items:
            field_name_sel = f'return_{item.pk}'
            field_name_qty = f'return_qty_{item.pk}'

            if field_name_sel in self.fields:
                is_selected = cleaned_data.get(field_name_sel, False)
                qty = cleaned_data.get(field_name_qty, 0) or 0

                if is_selected and qty > 0:
                    selected_items.append({
                        'sale_item': item,
                        'quantity': qty,
                        'unit_price': item.unit_price,
                        'line_total': Decimal(str(qty)) * item.unit_price,
                    })

        if not selected_items:
            raise ValidationError(
                _('Please select at least one item and specify a return quantity.')
            )

        # Store selected items on the form for the view to use
        self.selected_items = selected_items
        self.refund_amount = sum(item['line_total'] for item in selected_items)

        return cleaned_data


# Late import for Sum in ReturnItemsForm.__init__
from django.db.models import Sum  # noqa: E402