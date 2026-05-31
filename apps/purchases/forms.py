"""
MediPOS Purchases — Forms.

ModelForms and plain Forms for the purchase order workflow:
- PurchaseOrderForm: Creating/editing a PO header.
- PurchaseOrderItemForm: Adding line items to a PO.
- POReceiveForm: Confirming receipt of stock (not a ModelForm).
"""

from datetime import date

from django import forms
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import PurchaseOrder, PurchaseOrderItem
from apps.accounts.models import User
from apps.medicines.models import Medicine


class PurchaseOrderForm(forms.ModelForm):
    """
    ModelForm for creating or editing a PurchaseOrder header.

    Includes the supplier selection, expected delivery date, and internal
    notes. The PO number is auto-generated on first save.

    Fields:
        supplier: Required — select the supplier for this order.
        expected_delivery_date: Optional anticipated delivery date.
        notes: Optional internal notes.
    """

    class Meta:
        model = PurchaseOrder
        fields = (
            'supplier',
            'expected_delivery_date',
            'notes',
        )
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'expected_delivery_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': _('Add any internal notes...'),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """Initialize crispy-forms helper with Bootstrap 5 layout."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.template_pack = 'bootstrap5'
        self.helper.add_input(
            Submit('submit', _('Save Purchase Order'), css_class='btn btn-primary')
        )


class PurchaseOrderItemForm(forms.ModelForm):
    """
    ModelForm for adding a single line item to a purchase order.

    Each item links a medicine, quantity, unit price, batch number,
    and expiry date. The line_total is auto-calculated on save.

    Fields:
        medicine: Required — select the medicine to order.
        quantity: Required — number of units (default 1).
        unit_price: Required — purchase price per unit in BDT.
        batch_no: Optional — supplier's batch/lot number.
        expiry_date: Optional — supplier's expiry date.
    """

    class Meta:
        model = PurchaseOrderItem
        fields = (
            'medicine',
            'quantity',
            'unit_price',
            'batch_no',
            'expiry_date',
        )
        widgets = {
            'medicine': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(
                attrs={'class': 'form-control', 'min': '1'}
            ),
            'unit_price': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}
            ),
            'batch_no': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': _("Supplier's batch number"),
                }
            ),
            'expiry_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
        }

    def __init__(self, *args, **kwargs):
        """Initialize crispy-forms helper and filter to active medicines."""
        super().__init__(*args, **kwargs)
        self.fields['medicine'].queryset = Medicine.objects.filter(is_active=True)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.template_pack = 'bootstrap5'
        self.helper.add_input(
            Submit('submit', _('Add Item'), css_class='btn btn-success')
        )


class POReceiveForm(forms.Form):
    """
    Form for receiving/confirming stock delivery for a purchase order.

    This is NOT a ModelForm — the view handles the actual logic of creating
    Batch records and updating the PO status. This form simply collects
    the receiving user and optional notes.

    Fields:
        received_by: Required — Admin or Pharmacist who received the stock.
        notes: Optional — any delivery notes or discrepancies.
    """

    received_by = forms.ModelChoiceField(
        queryset=User.objects.filter(
            role__in=['ADMIN', 'PHARMACIST'],
            is_active=True,
        ),
        label=_('Received By'),
        help_text=_('Select the user who confirmed receipt of stock.'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    notes = forms.CharField(
        required=False,
        label=_('Receiving Notes'),
        help_text=_('Optional notes about the delivery (damage, discrepancies, etc.).'),
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('e.g., All items received in good condition...'),
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        """Initialize crispy-forms helper with Bootstrap 5."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.template_pack = 'bootstrap5'
        self.helper.add_input(
            Submit('submit', _('Confirm Receipt'), css_class='btn btn-success btn-lg')
        )