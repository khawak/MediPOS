"""
MediPOS Medicines — Admin Configuration.

Registers Category and Medicine models with the Django admin interface.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Category, Medicine


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Category model.

    Features:
        - List view with name, slug, active status, and creation date.
        - Search by name.
        - Auto-populated slug from name.
    """

    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_display_links = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('is_active',)
    ordering = ('name',)


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Medicine model.

    Features:
        - List view with key fields including stock and low-stock indicator.
        - Search across name, generic name, brand, and barcode.
        - Filter by category and active status.
        - Stock quantity is read-only (managed via inventory signals).
    """

    list_display = (
        'name',
        'brand',
        'category',
        'barcode',
        'selling_price',
        'stock_quantity',
        'is_low_stock',
        'is_active',
    )
    list_display_links = ('name',)
    search_fields = ('name', 'generic_name__name', 'brand', 'barcode')
    list_filter = ('category', 'is_active')
    list_per_page = 50
    readonly_fields = ('stock_quantity',)
    ordering = ('name',)
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'generic_name', 'brand', 'category', 'barcode', 'unit')
        }),
        (_('Pricing'), {
            'fields': ('purchase_price', 'selling_price', 'tax_rate')
        }),
        (_('Stock'), {
            'fields': ('stock_quantity', 'reorder_level')
        }),
        (_('Status & Details'), {
            'fields': ('is_active', 'description', 'image')
        }),
    )