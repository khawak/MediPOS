"""
MediPOS Customers — Forms.

Defines the CustomerForm ModelForm with crispy-forms Bootstrap 5 layout.
"""
from django import forms
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import Customer


class CustomerForm(forms.ModelForm):
    """
    ModelForm for creating and updating Customer instances.

    Uses crispy-forms with Bootstrap 5 template pack.
    """

    class Meta:
        """Form metadata bound to the Customer model."""
        model = Customer
        fields = [
            'name',
            'phone',
            'email',
            'address',
            'loyalty_points',
            'is_active',
            'notes',
        ]

    def __init__(self, *args, **kwargs):
        """Initialize crispy-forms helper with Bootstrap 5."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.template_pack = 'bootstrap5'
        self.helper.add_input(
            Submit('submit', _('Save Customer'), css_class='btn btn-primary')
        )