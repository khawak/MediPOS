"""
MediPOS Settings — Models.

Defines the ShopSettings singleton model for global store configuration.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class ShopSettings(models.Model):
    """
    Singleton model holding global shop configuration.

    Only one instance should ever exist (pk=1).  Use ShopSettings.get_settings()
    to retrieve or create the singleton.

    Attributes:
        shop_name: Display name of the pharmacy.
        shop_address: Physical address.
        shop_phone: Contact phone number.
        shop_email: Contact email address.
        shop_logo: Shop logo image.
        tin_number: Tax Identification Number.
        vat_number: VAT registration number.
        default_tax_rate: Default tax percentage applied to sales.
        currency_symbol: Currency symbol (e.g., ৳).
        currency_code: ISO currency code (e.g., BDT).
        receipt_footer: Text printed at the bottom of receipts.
        low_stock_threshold: Global low-stock warning threshold.
        created_at: Timestamp of creation.
        updated_at: Timestamp of last update.
    """

    shop_name = models.CharField(
        max_length=200,
        default='MediPOS Pharmacy',
        verbose_name=_('shop name'),
        help_text=_('Display name of the pharmacy.'),
    )
    shop_address = models.TextField(
        blank=True,
        verbose_name=_('shop address'),
        help_text=_('Physical address of the pharmacy.'),
    )
    shop_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('shop phone'),
        help_text=_('Contact phone number for the pharmacy.'),
    )
    shop_email = models.EmailField(
        blank=True,
        verbose_name=_('shop email'),
        help_text=_('Contact email address.'),
    )
    shop_logo = models.ImageField(
        upload_to='shop/',
        blank=True,
        null=True,
        verbose_name=_('shop logo'),
        help_text=_('Upload a logo for the pharmacy.'),
    )
    tin_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('TIN number'),
        help_text=_('Tax Identification Number.'),
    )
    vat_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('VAT number'),
        help_text=_('VAT registration number.'),
    )
    default_tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15.00,
        verbose_name=_('default tax rate'),
        help_text=_('Default tax percentage applied to sales.'),
    )
    currency_symbol = models.CharField(
        max_length=10,
        default='৳',
        verbose_name=_('currency symbol'),
        help_text=_('Symbol used to display prices (e.g., ৳, $, ₹).'),
    )
    currency_code = models.CharField(
        max_length=5,
        default='BDT',
        verbose_name=_('currency code'),
        help_text=_('ISO currency code (e.g., BDT, USD, INR).'),
    )
    receipt_footer = models.TextField(
        blank=True,
        default='Thank you for your purchase!',
        verbose_name=_('receipt footer'),
        help_text=_('Text printed at the bottom of receipts.'),
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        verbose_name=_('low stock threshold'),
        help_text=_('Global low-stock warning threshold.'),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('created at'),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('updated at'),
    )

    class Meta:
        verbose_name = _('Shop Settings')
        verbose_name_plural = _('Shop Settings')

    def __str__(self):
        """Return the shop name as the string representation."""
        return self.shop_name

    @classmethod
    def get_settings(cls):
        """
        Retrieve or create the singleton ShopSettings instance.

        Always returns the instance with pk=1.  Creates a default
        entry automatically if none exists.

        Returns:
            ShopSettings: The singleton settings object.
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        """
        Enforce the singleton pattern by always saving with pk=1.

        This prevents accidental creation of multiple settings rows.
        """
        self.pk = 1
        super().save(*args, **kwargs)