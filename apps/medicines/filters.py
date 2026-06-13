"""
MediPOS Medicines — Filters.

django-filter FilterSet for the Medicine list view.
"""
import django_filters
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from .models import Category, GenericName, Medicine


class MedicineFilter(django_filters.FilterSet):
    """
    FilterSet for the Medicine model.

    Provides:
        - search: Combined text search across name, generic_name, brand, and barcode.
        - category: Dropdown filter by Category.
        - is_active: Boolean toggle for active/inactive medicines.
        - low_stock: Boolean toggle to show only medicines with stock <= reorder_level.
    """

    search = django_filters.CharFilter(
        method='filter_search',
        label=_('Search'),
        widget=django_filters.widgets.forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': _('Search by name, generic, brand, or barcode...'),
            }
        ),
    )

    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.filter(is_active=True),
        empty_label=_('All Categories'),
        label=_('Category'),
        widget=django_filters.widgets.forms.Select(attrs={'class': 'form-select'}),
    )

    generic_name = django_filters.ModelChoiceFilter(
        queryset=GenericName.objects.all(),
        empty_label=_('All Generic Names'),
        label=_('Generic Name'),
        widget=django_filters.widgets.forms.Select(attrs={'class': 'form-select'}),
    )

    is_active = django_filters.BooleanFilter(
        method='filter_active',
        label=_('Active Only'),
        widget=django_filters.widgets.forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    low_stock = django_filters.BooleanFilter(
        method='filter_low_stock',
        label=_('Low Stock Only'),
        widget=django_filters.widgets.forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = Medicine
        fields = ['search', 'category', 'generic_name', 'is_active', 'low_stock']

    def filter_active(self, queryset, name, value):
        """
        Filter to show only active medicines when the checkbox is ticked.

        When unchecked (or missing from GET params), show all medicines.
        This prevents the BooleanFilter from defaulting to ``WHERE NOT is_active``
        on initial page load when the checkbox is not submitted.
        """
        if value:
            return queryset.filter(is_active=True)
        return queryset

    def filter_search(self, queryset, name, value):
        """
        Filter the queryset by searching across name, generic_name, brand, and barcode.

        Args:
            queryset: The initial Medicine queryset.
            name: The filter field name ('search').
            value: The search term entered by the user.

        Returns:
            Filtered queryset matching any of the search fields.
        """
        if not value:
            return queryset
        query = (
            Q(name__icontains=value)
            | Q(generic_name__name__icontains=value)
            | Q(brand__icontains=value)
            | Q(barcode__icontains=value)
        )
        return queryset.filter(query)

    def filter_low_stock(self, queryset, name, value):
        """
        Filter to show only medicines whose stock is at or below reorder level.

        Args:
            queryset: The initial Medicine queryset.
            name: The filter field name ('low_stock').
            value: Boolean from the filter toggle.

        Returns:
            Filtered queryset or the original if value is False.
        """
        if value:
            return queryset.filter(stock_quantity__lte=F('reorder_level'))
        return queryset