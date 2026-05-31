"""
MediPOS Suppliers — Forms.

Defines the SupplierForm ModelForm, and SupplierImportForm for CSV bulk import,
all with crispy-forms Bootstrap 5 layout.
"""
import csv
import io

from django import forms
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import Supplier


class SupplierForm(forms.ModelForm):
    """
    ModelForm for creating and updating Supplier instances.

    Uses crispy-forms with Bootstrap 5 template pack.
    Note: balance is excluded — it is auto-managed by PaymentTransaction.
    """

    class Meta:
        model = Supplier
        fields = [
            'name',
            'contact_person',
            'phone',
            'email',
            'address',
            'notes',
            'is_active',
        ]

    def __init__(self, *args, **kwargs):
        """Initialize crispy-forms helper with Bootstrap 5."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.template_pack = 'bootstrap5'
        self.helper.add_input(
            Submit('submit', _('Save Supplier'), css_class='btn btn-primary')
        )


class SupplierImportForm(forms.Form):
    """
    Form for uploading a CSV file containing supplier records for bulk import.

    The CSV file must have a .csv extension and follow the defined format:
    name, contact_person, phone, email, address, notes
    """

    csv_file = forms.FileField(
        label=_('CSV File'),
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        help_text=_('Select a CSV file with the supplier import template format.'),
    )

    def __init__(self, *args, **kwargs):
        """Initialize crispy-forms helper with Bootstrap 5."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.template_pack = 'bootstrap5'
        self.helper.add_input(
            Submit('submit', _('Import Suppliers'), css_class='btn btn-success')
        )