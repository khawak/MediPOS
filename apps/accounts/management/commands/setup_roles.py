"""
Management command to set up role-based groups and permissions for MediPOS.

Usage:
    python manage.py setup_roles

Creates three groups (Admin, Pharmacist, Cashier) and assigns appropriate
Django permissions to each based on their role requirements.
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Set up role groups and assign permissions.

    Creates the Admin, Pharmacist, and Cashier groups if they don't already
    exist, and grants each group the appropriate set of Django model-level
    permissions.
    """

    help = 'Create role-based groups and assign permissions for MediPOS.'

    # ── Permission Configuration ────────────────────────────────────────────
    # App labels whose model-level permissions are assigned to each role.
    ROLE_PERMISSIONS = {
        'Admin': {
            # Admin gets ALL permissions for every MediPOS app + auth
            'accounts': 'all',
            'medicines': 'all',
            'inventory': 'all',
            'suppliers': 'all',
            'customers': 'all',
            'sales': 'all',
            'purchases': 'all',
            'returns': 'all',
            'reports': 'all',
            # Full CRUD on users (via auth content type — custom user lives in accounts)
            'sessions': 'all',
            'contenttypes': 'all',
        },
        'Pharmacist': {
            # Pharmacist: medicines, inventory, purchases, reports (no settings, no user mgmt)
            'medicines': 'all',
            'inventory': 'all',
            'suppliers': 'all',
            'purchases': 'all',
            'reports': ['view'],
            'sales': ['view'],
            'returns': ['view'],
            'customers': ['view'],
        },
        'Cashier': {
            # Cashier: POS/sales only, view-only on medicines/inventory
            'sales': 'all',
            'returns': ['add', 'view'],
            'customers': ['view'],
            'medicines': ['view'],
            'inventory': ['view'],
        },
    }

    def handle(self, *args, **options):
        """Execute the role setup command."""
        self.stdout.write('Setting up MediPOS role groups and permissions...\n')

        for group_name, app_permissions in self.ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'  Created group: {group_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'  Group already exists: {group_name}')
                )

            # Clear existing permissions before reassigning
            group.permissions.clear()

            assigned_count = self._assign_permissions(group, app_permissions)
            self.stdout.write(
                f'    Assigned {assigned_count} permissions to "{group_name}".'
            )

        self.stdout.write(self.style.SUCCESS('\nRole setup complete.'))

    def _assign_permissions(self, group, app_permissions):
        """
        Assign permissions to a group based on the configuration dict.

        Args:
            group: The Django Group instance.
            app_permissions: Dict mapping app_label → 'all' or list of codename prefixes.

        Returns:
            int: Total number of permissions assigned.
        """
        assigned_count = 0

        for app_label, perms in app_permissions.items():
            try:
                # Get all content types for this app label
                content_types = ContentType.objects.filter(app_label=app_label)
            except ContentType.DoesNotExist:
                self.stdout.write(
                    self.style.NOTICE(
                        f'      No content types found for app "{app_label}".'
                    )
                )
                continue

            for ct in content_types:
                if perms == 'all':
                    # Grant all permissions for this model
                    model_perms = Permission.objects.filter(content_type=ct)
                    group.permissions.add(*model_perms)
                    assigned_count += model_perms.count()
                elif isinstance(perms, list):
                    # Grant specific permission types (view, add, change, delete)
                    for perm_type in perms:
                        codename = f'{perm_type}_{ct.model}'
                        try:
                            perm = Permission.objects.get(
                                content_type=ct,
                                codename=codename,
                            )
                            group.permissions.add(perm)
                            assigned_count += 1
                        except Permission.DoesNotExist:
                            self.stdout.write(
                                self.style.NOTICE(
                                    f'      Permission "{codename}" not found for '
                                    f'{ct.app_label}.{ct.model}.'
                                )
                            )

        return assigned_count