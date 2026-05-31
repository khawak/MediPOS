"""
MediPOS Returns & Refunds — Admin Configuration.

Registers SalesReturn and SalesReturnItem with the Django admin
interface, including inline item management for sales returns.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import SalesReturn, SalesReturnItem


class SalesReturnItemInline(admin.TabularInline):
    """
    Inline admin for SalesReturnItem within the SalesReturn admin.

    Allows viewing returned line items directly on the sales return form.
    Displays the medicine, quantity returned, unit price, and line total.
    """

    model = SalesReturnItem
    extra = 0
    fields = (
        'sale_item',
        'quantity',
        'unit_price',
        'line_total',
    )
    readonly_fields = ('line_total',)
    can_delete = False
    show_change_link = True
    verbose_name = _('Returned Item')
    verbose_name_plural = _('Returned Items')

    def has_add_permission(self, request, obj=None):
        """Prevent adding return items via inline — handled in views."""
        return False


@admin.register(SalesReturn)
class SalesReturnAdmin(admin.ModelAdmin):
    """
    Admin configuration for SalesReturn.

    Features:
        - List display with sale invoice, return date, refund amount, processor.
        - Date hierarchy on return_date for chronological browsing.
        - Inline display of returned items.
        - Read-only timestamps and refund amount.
    """

    list_display = (
        'sale_invoice',
        'return_date',
        'refund_amount',
        'processed_by',
        'created_at',
    )
    date_hierarchy = 'return_date'
    search_fields = ('sale__invoice_no', 'reason')
    readonly_fields = ('refund_amount', 'created_at', 'updated_at')

    inlines = [SalesReturnItemInline]

    fieldsets = (
        (_('Return Information'), {
            'fields': (
                'sale',
                'return_date',
                'refund_amount',
                'reason',
                'processed_by',
            ),
        }),
        (_('Notes'), {
            'fields': ('notes',),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def sale_invoice(self, obj):
        """Display the sale invoice number in the admin list."""
        return obj.sale.invoice_no

    sale_invoice.short_description = _('Invoice No')
    sale_invoice.admin_order_field = 'sale__invoice_no'


@admin.register(SalesReturnItem)
class SalesReturnItemAdmin(admin.ModelAdmin):
    """
    Standalone admin for SalesReturnItem.

    Allows cross-reference queries by sales return or medicine name.
    """

    list_display = (
        'sales_return',
        'sale_item',
        'quantity',
        'unit_price',
        'line_total',
    )
    search_fields = (
        'sales_return__sale__invoice_no',
        'sale_item__medicine__name',
    )
    readonly_fields = ('line_total',)