"""
MediPOS Accounts — Admin Configuration.

Registers the custom User model with Django's admin site, providing
tailored list displays, search, filters, and fieldset layouts.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom ModelAdmin for the MediPOS User model.

    Extends Django's default UserAdmin to include the role, phone, and
    avatar fields in list display, search, filtering, and fieldset layouts.
    """

    # ── List Display ────────────────────────────────────────────────────
    list_display = (
        'username',
        'email',
        'role',
        'phone',
        'is_active',
        'is_staff',
        'date_joined',
    )
    list_display_links = ('username', 'email')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
    )
    ordering = ('-date_joined',)

    # ── Fieldsets ───────────────────────────────────────────────────────
    fieldsets = (
        (None, {
            'fields': ('username', 'password'),
        }),
        (_('Personal info'), {
            'fields': (
                'first_name',
                'last_name',
                'email',
                'phone',
                'avatar',
            ),
        }),
        (_('Role & Permissions'), {
            'fields': (
                'role',
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            ),
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'date_joined'),
        }),
    )

    # ── Fieldsets for Add View ──────────────────────────────────────────
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'first_name',
                'last_name',
                'phone',
                'role',
                'password1',
                'password2',
            ),
        }),
    )

    # ── Read-only Fields ────────────────────────────────────────────────
    readonly_fields = ('created_at', 'updated_at', 'date_joined', 'last_login')