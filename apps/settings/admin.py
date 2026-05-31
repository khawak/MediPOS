"""
MediPOS Settings — Admin Configuration.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import ShopSettings


@admin.register(ShopSettings)
class ShopSettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for the singleton ShopSettings model.

    Restricts delete permission since the singleton should never
    be deleted, and prevents adding a second instance.
    """

    fieldsets = (
        (_('Shop Information'), {
            'fields': ('shop_name', 'shop_address', 'shop_phone', 'shop_email', 'shop_logo'),
        }),
        (_('Tax & Currency'), {
            'fields': ('tin_number', 'vat_number', 'default_tax_rate', 'currency_symbol', 'currency_code'),
        }),
        (_('Defaults & Receipt'), {
            'fields': ('low_stock_threshold', 'receipt_footer'),
        }),
    )

    def has_add_permission(self, request):
        """Prevent adding a second settings instance."""
        return not ShopSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting the singleton settings."""
        return False