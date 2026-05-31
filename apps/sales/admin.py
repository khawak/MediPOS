"""
MediPOS Sales — Admin Configuration.

Registers Sale and SaleItem models with the Django admin interface,
providing inline editing of sale items within the sale form.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    """
    Inline admin for SaleItem records within a Sale.

    Displays medicine, quantity, unit price, and line total in a
    compact tabular format inside the parent Sale admin form.
    """

    model = SaleItem
    extra = 0
    readonly_fields = ('line_total',)
    fields = ('medicine', 'batch', 'quantity', 'unit_price', 'discount', 'tax_rate', 'line_total')

    def has_add_permission(self, request, obj=None):
        """Allow adding items to existing sales."""
        return obj is not None

    def has_delete_permission(self, request, obj=None):
        """Allow deleting items from existing sales."""
        return obj is not None


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Sale model.

    Provides list, search, filter, and detail views with inline
    SaleItem management and read-only total fields.
    """

    list_display = (
        'invoice_no',
        'customer',
        'cashier',
        'grand_total',
        'payment_mode',
        'status',
        'sale_date',
    )
    list_filter = ('status', 'payment_mode', 'sale_date')
    search_fields = ('invoice_no', 'customer__name', 'customer__phone')
    readonly_fields = (
        'invoice_no',
        'subtotal',
        'discount_amount',
        'tax_amount',
        'grand_total',
        'change_amount',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        (_('Transaction Info'), {
            'fields': (
                'invoice_no', 'status', 'customer', 'cashier',
                'sale_date', 'notes',
            ),
        }),
        (_('Financials'), {
            'fields': (
                'subtotal', 'discount_percent', 'discount_amount',
                'tax_amount', 'grand_total',
            ),
        }),
        (_('Payment'), {
            'fields': (
                'payment_mode', 'amount_paid', 'change_amount',
            ),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    inlines = [SaleItemInline]
    date_hierarchy = 'sale_date'

    def save_model(self, request, obj, form, change):
        """Auto-generate invoice_no on creation if not set."""
        if not obj.pk and not obj.invoice_no:
            from .models import generate_invoice_number
            obj.invoice_no = generate_invoice_number()
        super().save_model(request, obj, form, change)


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    """
    Admin configuration for the SaleItem model.

    Provides a standalone list view for all sale items with
    filtering by sale and medicine.
    """

    list_display = ('sale', 'medicine', 'quantity', 'unit_price', 'discount', 'line_total')
    list_filter = ('sale__sale_date', 'medicine')
    search_fields = ('sale__invoice_no', 'medicine__name')
    readonly_fields = ('line_total',)
    autocomplete_fields = ('sale', 'medicine', 'batch')