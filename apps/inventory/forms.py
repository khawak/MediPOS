"""
MediPOS Inventory — Forms.

ModelForm for Batch (Stock-In) and regular Form for Stock Adjustments.
"""
from django import forms
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import Batch, StockLedger
from apps.medicines.models import Medicine


class StockInForm(forms.ModelForm):
    """
    ModelForm for creating a new Batch (stock-in operation).

    Creating a Batch triggers a signal that auto-creates a StockLedger
    IN entry and updates Medicine.stock_quantity.

    The medicine dropdown is filtered to show only active medicines.
    """

    class Meta:
        model = Batch
        fields = (
            'medicine',
            'supplier',
            'batch_no',
            'manufacture_date',
            'expiry_date',
            'quantity',
            'purchase_price',
            'purchase_order',
            'is_active',
        )
        widgets = {
            'manufacture_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'expiry_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'batch_no': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': _('Batch / lot number')}
            ),
            'quantity': forms.NumberInput(
                attrs={'class': 'form-control', 'min': '1'}
            ),
            'purchase_price': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}
            ),
            'purchase_order': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': _('Optional PO reference')}
            ),
        }

    def __init__(self, *args, **kwargs):
        """Initialize crispy-forms helper and set medicine queryset."""
        super().__init__(*args, **kwargs)
        # On GET (new): empty queryset — medicine chosen via AJAX search.
        # On GET (edit): queryset of the existing medicine only.
        # On POST: widen to the submitted PK so validation passes.
        if args and args[0]:
            submitted_id = args[0].get('medicine')
            if submitted_id:
                self.fields['medicine'].queryset = Medicine.objects.filter(
                    pk=submitted_id
                )
            else:
                self.fields['medicine'].queryset = Medicine.objects.none()
        elif self.instance and self.instance.pk:
            self.fields['medicine'].queryset = Medicine.objects.filter(
                pk=self.instance.medicine_id
            )
        else:
            self.fields['medicine'].queryset = Medicine.objects.none()
        self.fields['medicine'].widget.attrs.update({'class': 'form-select'})
        self.fields['supplier'].widget.attrs.update({'class': 'form-select'})

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.template_pack = 'bootstrap5'
        self.helper.add_input(
            Submit('submit', _('Add Stock'), css_class='btn btn-success')
        )


class StockAdjustmentForm(forms.Form):
    """
    Form for creating a manual stock adjustment (loss, damage, correction, other).

    Submitting this form will create a StockLedger entry with a negative
    quantity (deduction), which triggers the signal to update
    Medicine.stock_quantity.

    This is NOT a ModelForm — the view creates the StockLedger entry manually.
    """

    ADJUSTMENT_TYPES = [
        ('LOSS', _('Loss / Theft')),
        ('DAMAGE', _('Damage / Expiry')),
        ('CORRECTION', _('Correction')),
        ('OTHER', _('Other')),
    ]

    medicine = forms.ModelChoiceField(
        queryset=Medicine.objects.none(),
        label=_('Medicine'),
        help_text=_('Select the medicine to adjust.'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    adjustment_type = forms.ChoiceField(
        choices=ADJUSTMENT_TYPES,
        label=_('Adjustment Type'),
        help_text=_('Reason for the stock adjustment.'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    quantity = forms.IntegerField(
        min_value=1,
        label=_('Quantity'),
        help_text=_('Number of units to deduct from stock.'),
        widget=forms.NumberInput(
            attrs={'class': 'form-control', 'min': '1'}
        ),
    )
    reason = forms.CharField(
        label=_('Reason'),
        help_text=_('Detailed explanation for this adjustment.'),
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Explain why this adjustment is needed...'),
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        """Initialize crispy-forms helper and set medicine queryset."""
        super().__init__(*args, **kwargs)
        # On POST, widen queryset to the submitted PK so validation passes.
        # On GET, keep empty — medicine is chosen via AJAX search widget.
        if args and args[0]:
            submitted_id = args[0].get('medicine')
            if submitted_id:
                self.fields['medicine'].queryset = Medicine.objects.filter(
                    pk=submitted_id, is_active=True
                )
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.template_pack = 'bootstrap5'
        self.helper.add_input(
            Submit('submit', _('Submit Adjustment'), css_class='btn btn-warning')
        )