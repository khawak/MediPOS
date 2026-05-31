"""
MediPOS Suppliers — Admin Configuration.

Registers the Supplier model with the Django admin site.
"""
from django.contrib import admin

from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    """
    Admin interface for the Supplier model.

    Provides search, filtering, and a clean list display for managing suppliers.
    """

    list_display = (
        'name',
        'contact_person',
        'phone',
        'email',
        'is_active',
        'created_at',
    )
    search_fields = ('name', 'contact_person', 'phone', 'email')
    list_filter = ('is_active',)