"""
MediPOS Payments — Admin Configuration.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import DueSettlement, PaymentTransaction


class DueSettlementInline(admin.TabularInline):
    """Inline for DueSettlements within a PaymentTransaction."""
    model = DueSettlement
    extra = 0
    fields = ('sale', 'purchase_order', 'amount_settled')


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    """Admin configuration for PaymentTransaction."""

    list_display = (
        'payee_name',
        'payee_type_name',
        'transaction_type',
        'amount',
        'payment_method',
        'transaction_date',
        'created_by',
        'created_at',
    )
    list_filter = (
        'transaction_type',
        'payment_method',
        'content_type',
        'transaction_date',
    )
    search_fields = (
        'reference',
        'note',
    )
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    list_per_page = 25
    inlines = [DueSettlementInline]

    fieldsets = (
        (_('Transaction Details'), {
            'fields': (
                'content_type',
                'object_id',
                'amount',
                'transaction_type',
                'payment_method',
                'transaction_date',
            ),
        }),
        (_('Invoice / PO Links'), {
            'fields': ('sale', 'purchase_order'),
        }),
        (_('Reference'), {
            'fields': ('reference', 'note'),
        }),
        (_('Metadata'), {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(DueSettlement)
class DueSettlementAdmin(admin.ModelAdmin):
    """Admin configuration for DueSettlement."""

    list_display = (
        'payment',
        'sale',
        'purchase_order',
        'amount_settled',
        'created_at',
    )
    list_filter = ('created_at',)
    search_fields = ('payment__reference',)
    date_hierarchy = 'created_at'