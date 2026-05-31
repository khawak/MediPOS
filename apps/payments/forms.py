"""
MediPOS Payments — Forms.

Defines PaymentForm for recording customer/supplier payments and advances,
and DueSettlementFormSet for settling specific invoices/POs.
"""
from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import DueSettlement, PaymentTransaction


class PaymentForm(forms.ModelForm):
    """
    Form for recording a payment or advance for a Customer or Supplier.

    The invoice/PO FK field is dynamically added in __init__ based on
    payee_type — only the relevant one is included, avoiding
    validation issues with unrendered/irrelevant fields.
    """

    class Meta:
        model = PaymentTransaction
        fields = [
            'amount',
            'transaction_type',
            'payment_method',
            'reference',
            'note',
            'transaction_date',
        ]
        widgets = {
            'amount': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0.01',
                    'placeholder': _('Enter amount...'),
                }
            ),
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'reference': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': _('Cheque #, transaction ID...'),
                }
            ),
            'note': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 2,
                    'placeholder': _('Optional notes...'),
                }
            ),
            'transaction_date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),
        }

    def __init__(self, *args, payee_type=None, payee=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default transaction_date to today
        if not self.initial.get('transaction_date'):
            self.initial['transaction_date'] = timezone.now().date()

        # Dynamically add the relevant FK field based on payee type.
        # We do NOT add both fields — only the one that applies.
        if payee_type == 'customer':
            from apps.sales.models import Sale
            self.fields['sale'] = forms.ModelChoiceField(
                queryset=(
                    Sale.objects.filter(
                        customer=payee,
                        status='COMPLETED',
                    ).exclude(grand_total__lte=0).order_by('-sale_date')
                    if payee else Sale.objects.none()
                ),
                required=False,
                label=_('Apply to Invoice (optional)'),
                widget=forms.Select(attrs={'class': 'form-select'}),
            )
        elif payee_type == 'supplier':
            from apps.purchases.models import PurchaseOrder
            self.fields['purchase_order'] = forms.ModelChoiceField(
                queryset=(
                    PurchaseOrder.objects.filter(
                        supplier=payee,
                        status='RECEIVED',
                    ).order_by('-order_date')
                    if payee else PurchaseOrder.objects.none()
                ),
                required=False,
                label=_('Apply to PO (optional)'),
                widget=forms.Select(attrs={'class': 'form-select'}),
            )


class DueSettlementForm(forms.ModelForm):
    """Form for a single DueSettlement row within the formset."""

    class Meta:
        model = DueSettlement
        fields = ['sale', 'purchase_order', 'amount_settled']

    def __init__(self, *args, payee_type=None, payee=None, **kwargs):
        super().__init__(*args, **kwargs)
        if payee_type == 'customer' and payee:
            from apps.sales.models import Sale
            self.fields['sale'].queryset = Sale.objects.filter(
                customer=payee,
                status='COMPLETED',
            ).exclude(grand_total__lte=0).order_by('-sale_date')
            self.fields['purchase_order'].widget = forms.HiddenInput()
            self.fields['purchase_order'].required = False
        elif payee_type == 'supplier' and payee:
            from apps.purchases.models import PurchaseOrder
            self.fields['purchase_order'].queryset = PurchaseOrder.objects.filter(
                supplier=payee,
                status='RECEIVED',
            ).order_by('-order_date')
            self.fields['sale'].widget = forms.HiddenInput()
            self.fields['sale'].required = False


DueSettlementFormSet = forms.inlineformset_factory(
    PaymentTransaction,
    DueSettlement,
    form=DueSettlementForm,
    fields=['sale', 'purchase_order', 'amount_settled'],
    extra=3,
    can_delete=True,
)