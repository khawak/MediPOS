"""
MediPOS Settings — Context Processors.

Exposes the singleton ShopSettings instance to all templates
so shop name, logo, address, phone, email can be displayed
on invoices, receipts, and reports.
"""
from .models import ShopSettings


def shop_settings(request):
    """
    Make the ShopSettings singleton available in all templates.

    Usage in templates:
        {{ shop_settings.shop_name }}
        {{ shop_settings.shop_logo.url }}
        {{ shop_settings.shop_address }}
        {{ shop_settings.shop_phone }}
        {{ shop_settings.shop_email }}
    """
    return {'shop_settings': ShopSettings.get_settings()}