"""
MediPOS Medicines — Models.

Defines Category and Medicine models for the pharmacy inventory system.
"""
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """
    Product category for grouping medicines (e.g., Antibiotics, Pain Relief).

    Attributes:
        name: Display name of the category (unique).
        slug: URL-friendly identifier derived from name.
        description: Optional description of the category.
        is_active: Whether the category is visible/usable.
        created_at: Timestamp of creation.
        updated_at: Timestamp of last update.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('name'),
        help_text=_('Display name of the category.'),
    )
    slug = models.SlugField(
        max_length=120,
        unique=True,
        verbose_name=_('slug'),
        help_text=_('URL-friendly identifier (auto-generated from name).'),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('description'),
        help_text=_('Optional description of this category.'),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('is active'),
        help_text=_('Designates whether this category is visible in the system.'),
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
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['name']

    def __str__(self):
        """Return the category name."""
        return self.name

    def save(self, *args, **kwargs):
        """Auto-populate slug from name on creation or name change."""
        if not self.slug or (self.pk and self.name != self.__class__.objects.get(pk=self.pk).name):
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return the URL to the category list view."""
        return reverse('medicines:category_list')


class GenericName(models.Model):
    """
    Controlled vocabulary of INN / generic drug names (e.g. Paracetamol, Amoxicillin).
    """

    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name=_('name'),
        help_text=_('International non-proprietary name (INN) of the drug.'),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('description'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('updated at'))

    class Meta:
        verbose_name = _('Generic Name')
        verbose_name_plural = _('Generic Names')
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('medicines:generic_name_list')


class Medicine(models.Model):
    """
    Medicine / product record in the pharmacy inventory.

    Attributes:
        name: Trade/brand name of the medicine.
        generic_name: Scientific/generic name (e.g., Paracetamol).
        brand: Brand or manufacturer name.
        category: ForeignKey to Category for grouping.
        barcode: Unique SKU or barcode identifier.
        unit: Unit of measurement (Pcs, Strip, Bottle, Box, etc.).
        purchase_price: Cost price per unit.
        selling_price: Retail price per unit.
        tax_rate: Tax percentage (default 15% BDT VAT).
        reorder_level: Low-stock alert threshold.
        stock_quantity: Current stock (denormalized, updated via signals).
        description: Optional description.
        is_active: Whether the medicine is active in the system.
        image: Optional product image.
        created_at: Timestamp of creation.
        updated_at: Timestamp of last update.
    """

    name = models.CharField(
        max_length=200,
        verbose_name=_('name'),
        help_text=_('Trade or brand name of the medicine.'),
    )
    generic_name = models.ForeignKey(
        'GenericName',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medicines',
        verbose_name=_('generic name'),
        help_text=_('INN / generic drug name (e.g., Paracetamol).'),
    )
    brand = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('brand'),
        help_text=_('Brand or manufacturer name.'),
    )
    category = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medicines',
        verbose_name=_('category'),
        help_text=_('Product category for grouping.'),
    )
    barcode = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        verbose_name=_('barcode'),
        help_text=_('Unique SKU or barcode identifier.'),
    )
    unit = models.CharField(
        max_length=50,
        default='Pcs',
        verbose_name=_('unit'),
        help_text=_('Unit of measurement (e.g., Pcs, Strip, Bottle, Box).'),
    )
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_('purchase price'),
        help_text=_('Cost price per unit in BDT.'),
    )
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_('selling price'),
        help_text=_('Retail selling price per unit in BDT.'),
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15.00,
        verbose_name=_('tax rate'),
        help_text=_('Tax percentage applied (default 15%% BDT VAT).'),
    )
    reorder_level = models.PositiveIntegerField(
        default=10,
        verbose_name=_('reorder level'),
        help_text=_('Low-stock alert threshold; triggers reorder notification.'),
    )
    stock_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name=_('stock quantity'),
        help_text=_('Current stock on hand (managed by inventory).'),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('description'),
        help_text=_('Optional description or usage notes.'),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('is active'),
        help_text=_('Designates whether this medicine is active in the system.'),
    )
    image = models.ImageField(
        upload_to='medicines/',
        blank=True,
        null=True,
        verbose_name=_('image'),
        help_text=_('Optional product image.'),
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
        verbose_name = _('Medicine')
        verbose_name_plural = _('Medicines')
        ordering = ['name']
        indexes = [
            models.Index(fields=['barcode']),
            models.Index(fields=['name']),
        ]
        unique_together = [['name', 'brand', 'generic_name']]

    def __str__(self):
        """Return name with brand if available, otherwise just the name."""
        if self.brand:
            return f'{self.name} ({self.brand})'
        return self.name

    def get_absolute_url(self):
        """Return the URL to the medicine detail view."""
        return reverse('medicines:medicine_detail', kwargs={'pk': self.pk})

    @property
    def is_low_stock(self):
        """Return True if current stock is at or below the reorder level."""
        return self.stock_quantity <= self.reorder_level

    @property
    def profit_margin(self):
        """Return the difference between selling price and purchase price."""
        return self.selling_price - self.purchase_price