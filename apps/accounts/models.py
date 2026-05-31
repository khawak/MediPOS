"""
MediPOS Accounts — Custom User Model.

Defines the custom User model for the MediPOS pharmacy management system.
Supports role-based access control (RBAC) with ADMIN, PHARMACIST, and CASHIER roles.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom user model for MediPOS.

    Extends Django's AbstractUser to add role-based fields, phone, avatar,
    and timestamps for the pharmacy management system.

    Attributes:
        ROLE_CHOICES: Tuple of available roles and their display labels.
        role: The user's role determining permissions (ADMIN/PHARMACIST/CASHIER).
        phone: Optional contact phone number.
        avatar: Optional profile picture.
        created_at: Timestamp of user creation.
        updated_at: Timestamp of last user update.
    """

    class Role(models.TextChoices):
        """Available roles for MediPOS users with their permissions scope."""

        ADMIN = 'ADMIN', _('Administrator')
        PHARMACIST = 'PHARMACIST', _('Pharmacist')
        CASHIER = 'CASHIER', _('Cashier')

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CASHIER,
        verbose_name=_('role'),
        help_text=_('Role determines access permissions within the system.'),
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('phone number'),
        help_text=_('Contact phone number for the user.'),
    )

    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name=_('profile picture'),
        help_text=_('Optional profile picture for the user.'),
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
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']

    def __str__(self):
        """Return the user's full name, falling back to username."""
        full_name = self.get_full_name()
        return full_name if full_name else self.username

    def get_full_name(self):
        """
        Return the user's full name (first_name + last_name).

        Overridden to ensure consistent trimming.
        """
        full_name = f'{self.first_name} {self.last_name}'.strip()
        return full_name if full_name else self.username