"""
MediPOS Inventory — Filters.

django-filter FilterSets for the Batch list and StockLedger list views.
"""
from datetime import date

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import Batch, StockLedger
from apps.medicines.models import Medicine


class BatchFilter(django_filters.FilterSet):
    """
    FilterSet for the Batch model (inventory main page).

    Provides:
        - search: Combined text search across medicine name and batch number.
        - supplier_search: Text search across supplier name.
        - expiry_status: Choice filter (All, Expired, Expiring ≤30d, Expiring ≤60d, OK).
        - is_active: Boolean toggle for active/inactive batches.
    """

    EXPIRY_STATUS_CHOICES = [
        ('', _('All')),
        ('EXPIRED', _('Expired')),
        ('EXPIRING_30', _('Expiring ≤ 30 Days')),
        ('EXPIRING_60', _('Expiring ≤ 60 Days')),
        ('OK', _('OK (>60 Days)')),
    ]

    search = django_filters.CharFilter(
        method='filter_search',
        label=_('Search'),
        widget=django_filters.widgets.forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': _('Search medicine or batch #...'),
            }
        ),
    )

    supplier_search = django_filters.CharFilter(
        method='filter_supplier',
        label=_('Supplier'),
        widget=django_filters.widgets.forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': _('Search supplier name...'),
            }
        ),
    )

    expiry_status = django_filters.ChoiceFilter(
        choices=EXPIRY_STATUS_CHOICES,
        method='filter_expiry_status',
        label=_('Expiry Status'),
        widget=django_filters.widgets.forms.Select(attrs={'class': 'form-select'}),
    )

    is_active = django_filters.BooleanFilter(
        method='filter_is_active',
        label=_('Active Only'),
        widget=django_filters.widgets.forms.CheckboxInput(
            attrs={'class': 'form-check-input'}
        ),
    )

    class Meta:
        model = Batch
        fields = ['search', 'supplier_search', 'expiry_status']

    def filter_is_active(self, queryset, name, value):
        """
        Only filter to is_active=True when the checkbox is explicitly checked.
        When unchecked or absent from the request, return the full queryset.
        """
        if value:
            return queryset.filter(is_active=True)
        return queryset

    def filter_search(self, queryset, name, value):
        """
        Filter batches by searching across medicine name and batch number.

        Args:
            queryset: The initial Batch queryset.
            name: The filter field name ('search').
            value: The search term entered by the user.

        Returns:
            Filtered queryset matching any of the search fields.
        """
        if not value:
            return queryset
        return queryset.filter(
            Q(medicine__name__icontains=value)
            | Q(batch_no__icontains=value)
        )

    def filter_expiry_status(self, queryset, name, value):
        """
        Filter batches by their expiry status relative to today.

        Args:
            queryset: The initial Batch queryset.
            name: The filter field name ('expiry_status').
            value: One of '', 'EXPIRED', 'EXPIRING_30', 'EXPIRING_60', 'OK'.

        Returns:
            Filtered queryset based on expiry criteria.
        """
        today = date.today()
        if value == 'EXPIRED':
            return queryset.filter(expiry_date__lt=today)
        if value == 'EXPIRING_30':
            return queryset.filter(
                expiry_date__gte=today,
                expiry_date__lte=today + date.resolution * 30,
            )
        if value == 'EXPIRING_60':
            return queryset.filter(
                expiry_date__gte=today,
                expiry_date__lte=today + date.resolution * 60,
            )
        if value == 'OK':
            return queryset.filter(expiry_date__gt=today + date.resolution * 60)
        return queryset

    def filter_supplier(self, queryset, name, value):
        """
        Filter batches by searching across supplier name.

        Args:
            queryset: The initial Batch queryset.
            name: The filter field name ('supplier_search').
            value: The search term entered by the user.

        Returns:
            Filtered queryset matching supplier name (icontains).
        """
        if not value:
            return queryset
        return queryset.filter(supplier__name__icontains=value)


class StockLedgerFilter(django_filters.FilterSet):
    """
    FilterSet for the StockLedger model (audit trail view).

    Provides:
        - search: Text search across medicine name, batch number, and reference.
        - supplier_search: Text search across supplier name (via batch).
        - transaction_type: Dropdown filter by transaction type (IN/OUT/ADJ/RET).
        - date_from: Minimum date for the created_at timestamp.
        - date_to: Maximum date for the created_at timestamp.
    """

    search = django_filters.CharFilter(
        method='filter_search',
        label=_('Search'),
        widget=django_filters.widgets.forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': _('Search medicine, batch #, reference...'),
            }
        ),
    )

    supplier_search = django_filters.CharFilter(
        method='filter_supplier',
        label=_('Supplier'),
        widget=django_filters.widgets.forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': _('Search supplier name...'),
            }
        ),
    )

    transaction_type = django_filters.ChoiceFilter(
        choices=StockLedger.TRANSACTION_TYPES,
        empty_label=_('All Types'),
        label=_('Transaction Type'),
        widget=django_filters.widgets.forms.Select(attrs={'class': 'form-select'}),
    )

    date_from = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte',
        label=_('From Date'),
        widget=django_filters.widgets.forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        ),
    )

    date_to = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte',
        label=_('To Date'),
        widget=django_filters.widgets.forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        ),
    )

    class Meta:
        model = StockLedger
        fields = ['search', 'supplier_search', 'transaction_type', 'date_from', 'date_to']

    def filter_search(self, queryset, name, value):
        """
        Filter ledger entries by searching across medicine name,
        batch number, and reference field.

        Args:
            queryset: The initial StockLedger queryset.
            name: The filter field name ('search').
            value: The search term entered by the user.

        Returns:
            Filtered queryset matching any of the search fields.
        """
        if not value:
            return queryset
        return queryset.filter(
            Q(medicine__name__icontains=value)
            | Q(batch__batch_no__icontains=value)
            | Q(reference__icontains=value)
        )

    def filter_supplier(self, queryset, name, value):
        """
        Filter ledger entries by searching across supplier name (via batch).

        Args:
            queryset: The initial StockLedger queryset.
            name: The filter field name ('supplier_search').
            value: The search term entered by the user.

        Returns:
            Filtered queryset matching supplier name (icontains).
        """
        if not value:
            return queryset
        return queryset.filter(
            Q(batch__supplier__name__icontains=value)
        )