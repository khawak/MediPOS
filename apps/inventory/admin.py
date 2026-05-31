"""
MediPOS Inventory — Admin Configuration.

Registers Batch and StockLedger models with the Django admin interface.
"""
from django.contrib import admin

from .models import Batch, StockLedger


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Batch model.

    Features:
        - List view with medicine, batch_no, supplier, quantity, expiry,
          and computed expiry status fields.
        - Search by medicine name and batch number.
        - Filter by medicine and active status.
    """

    list_display = (
        'medicine',
        'batch_no',
        'supplier',
        'quantity',
        'expiry_date',
        'is_expired',
        'is_expiring_soon',
    )
    search_fields = ('medicine__name', 'batch_no')
    list_filter = ('medicine', 'is_active')
    ordering = ('expiry_date',)


@admin.register(StockLedger)
class StockLedgerAdmin(admin.ModelAdmin):
    """
    Admin configuration for the StockLedger model.

    Features:
        - List view with medicine, transaction type, quantity, batch,
          reference, created_by, and timestamp.
        - Search by medicine name.
        - Filter by transaction type.
        - All fields except 'note' are read-only (audit trail).
    """

    list_display = (
        'medicine',
        'transaction_type',
        'quantity',
        'batch',
        'reference',
        'created_by',
        'created_at',
    )
    search_fields = ('medicine__name',)
    list_filter = ('transaction_type',)
    readonly_fields = (
        'medicine',
        'batch',
        'transaction_type',
        'quantity',
        'reference',
        'created_by',
        'created_at',
    )
    ordering = ('-created_at',)