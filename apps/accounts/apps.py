"""
MediPOS Accounts App Configuration.

Registers signal handlers for the custom User model when the app is ready.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration class for the MediPOS Accounts app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Accounts'

    def ready(self):
        """
        Import and register signal handlers when the app is fully loaded.

        This ensures that the post_save signal for automatic group
        assignment is connected before the app starts handling requests.
        """
        # pylint: disable=import-outside-toplevel,unused-import
        import apps.accounts.signals  # noqa: F401