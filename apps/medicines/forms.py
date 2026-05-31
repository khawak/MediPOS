"""
MediPOS Medicines — Forms.

Form classes for Category, Medicine, and CSV bulk import.
"""
import csv
import io

from django import forms
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import Category, Medicine


class CategoryForm(forms.ModelForm):
    """
    ModelForm for creating and updating Category instances.

    Uses crispy-forms with Bootstrap 5 layout.
    """

    class Meta:
        model = Category
        fields = ('name', 'description', 'is_active')

    def __init__(self, *args, **kwargs):
        """Initialize crispy-forms helper with Bootstrap 5."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.template_pack = 'bootstrap5'
        self.helper.add_input(Submit('submit', _('Save Category'), css_class='btn btn-primary'))


class MedicineForm(forms.ModelForm):
    """
    ModelForm for creating and updating Medicine instances.

    Excludes stock_quantity, which is managed by the inventory system.
    """

    class Meta:
        model = Medicine
        exclude = ('stock_quantity',)

    def __init__(self, *args, **kwargs):
        """Initialize crispy-forms helper with Bootstrap 5."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.template_pack = 'bootstrap5'
        self.helper.add_input(Submit('submit', _('Save Medicine'), css_class='btn btn-primary'))


class MedicineImportForm(forms.Form):
    """
    Form for uploading a CSV file containing medicine records for bulk import.

    The CSV file must have a .csv extension and follow the defined format:
    name,generic_name,brand,category,barcode,unit,purchase_price,
    selling_price,tax_rate,reorder_level,description
    """

    csv_file = forms.FileField(
        label=_('CSV File'),
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        help_text=_('Select a CSV file with the medicine import template format.'),
    )

    def __init__(self, *args, **kwargs):
        """Initialize crispy-forms helper with Bootstrap 5."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.template_pack = 'bootstrap5'
        self.helper.add_input(Submit('submit', _('Import Medicines'), css_class='btn btn-success'))


class CategoryImportForm(forms.Form):
    """
    Form for uploading a CSV file containing category records for bulk import.

    The CSV file must have a .csv extension and follow the defined format:
    name, description, is_active
    """

    csv_file = forms.FileField(
        label=_('CSV File'),
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        help_text=_('Select a CSV file with the category import template format.'),
    )

    def __init__(self, *args, **kwargs):
        """Initialize crispy-forms helper with Bootstrap 5."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.template_pack = 'bootstrap5'
        self.helper.add_input(Submit('submit', _('Import Categories'), css_class='btn btn-success'))