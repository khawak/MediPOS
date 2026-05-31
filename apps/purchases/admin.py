"""
MediPOS Purchases — Admin Configuration.

Registers PurchaseOrder and PurchaseOrderItem with the Django admin
interface, including inline item management for purchase orders.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import PurchaseOrder, PurchaseOrderItem


class PurchaseOrderItemInline(admin.TabularInline):
    """
    Inline admin for PurchaseOrderItem within the PurchaseOrder admin.

    Allows adding/editing line items directly on the purchase order form.
    Displays the medicine, quantity, unit price, line total, and batch info.
    """

    model = PurchaseOrderItem
    extra = 0
    fields = (
        'medicine',
        'quantity',
        'unit_price',
        'line_total',
        'batch_no',
        'expiry_date',
    )
    readonly_fields = ('line_total',)
    autocomplete_fields = ['medicine']
    can_delete = True
    show_change_link = True
    verbose_name = _('Item')
    verbose_name_plural = _('Items')


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    """
    Admin configuration for PurchaseOrder.

    Features:
        - List display with key fields and computed items count.
        - Search by PO number.
        - Filter by status for quick workflow filtering.
        - Inline management of purchase order items.
        - Read-only total_amount and read-only po_number on change.
    """

    list_display = (
        'po_number',
        'supplier',
        'order_date',
        'status',
        'total_amount',
        'created_at',
    )
    list_filter = ('status', 'supplier')
    search_fields = ('po_number', 'supplier__name')
    readonly_fields = ('po_number', 'total_amount', 'created_at', 'updated_at')
    ordering = ['-order_date']
    date_hierarchy = 'order_date'

    inlines = [PurchaseOrderItemInline]

    fieldsets = (
        (_('Order Information'), {
            'fields': (
                'po_number',
                'supplier',
                'order_date',
                'expected_delivery_date',
                'status',
            ),
        }),
        (_('Financial'), {
            'fields': ('total_amount',),
        }),
        (_('People'), {
            'fields': ('created_by', 'received_by'),
        }),
        (_('Notes'), {
            'fields': ('notes',),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        Auto-set created_by on new POs and generate PO number if none.

        On first creation (not an edit), assigns the current user as
        created_by and generates a unique PO number.
        """
        if not change:
            obj.created_by = request.user
            if not obj.po_number:
                obj.po_number = generate_po_number()
        super().save_model(request, obj, form, change)


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    """
    Standalone admin for PurchaseOrderItem.

    Allows searching by PO number or medicine name and filtering by
    the parent purchase order. Useful for cross-reference queries.
    """

    list_display = (
        'purchase_order',
        'medicine',
        'quantity',
        'unit_price',
        'line_total',
        'batch_no',
        'expiry_date',
    )
    list_filter = ('purchase_order__status',)
    search_fields = (
        'purchase_order__po_number',
        'medicine__name',
        'batch_no',
    )
    readonly_fields = ('line_total',)
    autocomplete_fields = ['medicine', 'purchase_order']

# Import here to avoid circular import with the generate_po_number call
# in the save_model method above.
from .models import generate_po_number  # noqa: E402