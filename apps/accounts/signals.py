"""
MediPOS Accounts — Signal Handlers.

Contains signal handlers for the custom User model, including automatic
group assignment based on the user's role field.
"""

import logging

from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User

logger = logging.getLogger(__name__)

# Map role choices to group names used by setup_roles
ROLE_TO_GROUP = {
    User.Role.ADMIN: 'Admin',
    User.Role.PHARMACIST: 'Pharmacist',
    User.Role.CASHIER: 'Cashier',
}


@receiver(post_save, sender=User)
def assign_user_to_role_group(sender, instance, created, **kwargs):
    """
    Automatically assign a user to the appropriate Django Group based on role.

    This signal fires after every User save. It ensures that the user belongs
    to exactly one role group at a time — the group matching their current
    role. All other role groups are removed.

    Args:
        sender: The model class (User).
        instance: The actual User instance being saved.
        created: True if this is a new user; False for updates.
        **kwargs: Additional keyword arguments.
    """
    if instance.role not in ROLE_TO_GROUP:
        logger.warning(
            'User "%s" has unknown role "%s". Skipping group assignment.',
            instance.username,
            instance.role,
        )
        return

    try:
        group = Group.objects.get(name=ROLE_TO_GROUP[instance.role])
    except Group.DoesNotExist:
        logger.error(
            'Group "%s" does not exist. Run "manage.py setup_roles" to create it.',
            ROLE_TO_GROUP[instance.role],
        )
        return

    # Remove all other role groups and add only the current one
    current_groups = set(instance.groups.values_list('name', flat=True))
    role_group_names = set(ROLE_TO_GROUP.values())

    # Remove groups the user shouldn't have
    groups_to_remove = (current_groups & role_group_names) - {group.name}
    if groups_to_remove:
        instance.groups.remove(
            *Group.objects.filter(name__in=groups_to_remove)
        )

    # Add the correct group if not already a member
    if group.name not in current_groups:
        instance.groups.add(group)
        logger.info(
            'User "%s" added to group "%s".',
            instance.username,
            group.name,
        )