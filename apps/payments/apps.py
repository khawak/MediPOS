"""
MediPOS Payments — App Configuration.
"""
from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    """App configuration for the payments module."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.payments'
    verbose_name = 'Payments'