"""
MediPOS Inventory App Configuration.

Registers signal handlers for Batch and StockLedger models when the app
is ready, ensuring the auto-update chain (Batch → StockLedger →
Medicine.stock_quantity) is active.
"""

from django.apps import AppConfig


class InventoryConfig(AppConfig):
    """Configuration class for the MediPOS Inventory app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory'
    verbose_name = 'Inventory'

    def ready(self):
        """
        Import and register signal handlers when the app is fully loaded.

        This ensures that post_save signals for Batch (auto-create
        StockLedger) and StockLedger (auto-update Medicine.stock_quantity)
        are connected before the app starts handling requests.
        """
        # pylint: disable=import-outside-toplevel,unused-import
        import apps.inventory.signals  # noqa: F401