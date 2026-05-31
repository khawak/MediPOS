"""
MediPOS Reports — Forms.

Defines form classes for report filtering:
- DateRangeForm: Base form with from/to date fields.
- ReportFilterForm: Extended form with optional payment mode, category, and medicine filters.
"""

from datetime import date, timedelta

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.medicines.models import Category, Medicine
from apps.sales.models import Sale


class DateRangeForm(forms.Form):
    """
    Base form for selecting a date range for reports.

    Provides two date fields (from_date, to_date) with sensible defaults:
    from_date defaults to 30 days ago, to_date defaults to today.
    """

    from_date = forms.DateField(
        label=_('From Date'),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=lambda: date.today() - timedelta(days=30),
        help_text=_('Start date for the report.'),
    )
    to_date = forms.DateField(
        label=_('To Date'),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=date.today,
        help_text=_('End date for the report.'),
    )

    def clean(self):
        """
        Validate that from_date is not later than to_date.

        Returns:
            dict: The cleaned data.

        Raises:
            forms.ValidationError: If from_date > to_date.
        """
        cleaned_data = super().clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')

        if from_date and to_date and from_date > to_date:
            raise forms.ValidationError(
                _('From date cannot be later than to date.')
            )
        return cleaned_data


class ReportFilterForm(DateRangeForm):
    """
    Extended date-range form with optional filters for payment mode,
    category, and medicine selection.
    """

    payment_mode = forms.ChoiceField(
        label=_('Payment Mode'),
        choices=[('', _('All Payment Modes'))] + list(Sale.PaymentMode.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text=_('Filter by payment method.'),
    )
    category = forms.ModelChoiceField(
        label=_('Category'),
        queryset=Category.objects.filter(is_active=True),
        required=False,
        empty_label=_('All Categories'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text=_('Filter by medicine category.'),
    )
    medicine = forms.ModelChoiceField(
        label=_('Medicine'),
        queryset=Medicine.objects.filter(is_active=True),
        required=False,
        empty_label=_('All Medicines'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text=_('Filter by specific medicine.'),
    )