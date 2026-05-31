"""
MediPOS Purchases — Filters.

django-filter FilterSet for the PurchaseOrder list view. Supports
filtering by status, supplier, date range, and a combined search
across PO numbers.
"""

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import PurchaseOrder
from apps.suppliers.models import Supplier


class POFilter(django_filters.FilterSet):
    """
    FilterSet for the PurchaseOrder model.

    Provides:
        - status: ChoiceFilter for PO lifecycle states (DRAFT/ORDERED/etc.).
        - supplier: ModelChoiceFilter — dropdown of active suppliers.
        - date_from: DateFilter on order_date (greater than or equal).
        - date_to: DateFilter on order_date (less than or equal).
        - search: CharFilter that searches across po_number.
    """

    status = django_filters.ChoiceFilter(
        choices=PurchaseOrder.STATUS_CHOICES,
        empty_label=_('All Statuses'),
        label=_('Status'),
        widget=django_filters.widgets.forms.Select(
            attrs={'class': 'form-select'}
        ),
    )

    supplier = django_filters.ModelChoiceFilter(
        queryset=Supplier.objects.filter(is_active=True),
        empty_label=_('All Suppliers'),
        label=_('Supplier'),
        widget=django_filters.widgets.forms.Select(
            attrs={'class': 'form-select'}
        ),
    )

    date_from = django_filters.DateFilter(
        field_name='order_date',
        lookup_expr='gte',
        label=_('From Date'),
        widget=django_filters.widgets.forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        ),
    )

    date_to = django_filters.DateFilter(
        field_name='order_date',
        lookup_expr='lte',
        label=_('To Date'),
        widget=django_filters.widgets.forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        ),
    )

    search = django_filters.CharFilter(
        method='filter_search',
        label=_('Search'),
        widget=django_filters.widgets.forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': _('Search PO number...'),
            }
        ),
    )

    class Meta:
        model = PurchaseOrder
        fields = ['status', 'supplier', 'date_from', 'date_to', 'search']

    def filter_search(self, queryset, name, value):
        """
        Filter purchase orders by searching across PO numbers.

        Args:
            queryset: The initial PurchaseOrder queryset.
            name: The filter field name ('search').
            value: The search term entered by the user.

        Returns:
            Filtered queryset matching the search in po_number.
        """
        if not value:
            return queryset
        return queryset.filter(
            Q(po_number__icontains=value)
            | Q(supplier__name__icontains=value)
        )