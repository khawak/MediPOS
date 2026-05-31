"""
MediPOS Settings — Forms.
"""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Layout, Submit
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ShopSettings


class ShopSettingsForm(forms.ModelForm):
    """
    ModelForm for editing the singleton ShopSettings instance.

    Uses crispy-forms with Bootstrap 5 layout for consistent styling.
    """

    class Meta:
        model = ShopSettings
        fields = [
            'shop_name', 'shop_address', 'shop_phone', 'shop_email',
            'shop_logo', 'tin_number', 'vat_number', 'default_tax_rate',
            'currency_symbol', 'currency_code', 'receipt_footer',
            'low_stock_threshold',
        ]
        widgets = {
            'shop_address': forms.Textarea(attrs={'rows': 3}),
            'receipt_footer': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        """Set up crispy-forms layout with sections."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Div(
                Div(
                    Field('shop_name', wrapper_class='mb-3'),
                    css_class='col-md-6',
                ),
                Div(
                    Field('shop_logo', wrapper_class='mb-3'),
                    css_class='col-md-6',
                ),
                css_class='row',
            ),
            Field('shop_address', wrapper_class='mb-3'),
            Div(
                Div(Field('shop_phone', wrapper_class='mb-3'), css_class='col-md-4'),
                Div(Field('shop_email', wrapper_class='mb-3'), css_class='col-md-4'),
                css_class='row',
            ),
            Div(
                Div(Field('tin_number', wrapper_class='mb-3'), css_class='col-md-6'),
                Div(Field('vat_number', wrapper_class='mb-3'), css_class='col-md-6'),
                css_class='row',
            ),
            Div(
                Div(Field('default_tax_rate', wrapper_class='mb-3'), css_class='col-md-4'),
                Div(Field('currency_symbol', wrapper_class='mb-3'), css_class='col-md-4'),
                Div(Field('currency_code', wrapper_class='mb-3'), css_class='col-md-4'),
                css_class='row',
            ),
            Field('low_stock_threshold', wrapper_class='mb-3'),
            Field('receipt_footer', wrapper_class='mb-3'),
            Submit('submit', _('Save Settings'), css_class='btn btn-primary'),
        )