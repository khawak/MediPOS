"""
MediPOS Customers — Admin Configuration.

Registers the Customer model with the Django admin site.
"""
from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """
    Admin interface for the Customer model.

    Provides search, filtering, and a clean list display for managing customers.
    """

    list_display = (
        'name',
        'phone',
        'email',
        'loyalty_points',
        'is_active',
        'created_at',
    )
    search_fields = ('name', 'phone', 'email')
    list_filter = ('is_active',)