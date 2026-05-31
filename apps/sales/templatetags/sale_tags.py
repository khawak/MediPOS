"""
MediPOS Sales — Custom Template Tags.

Provides custom filters for formatting monetary values and other
display helpers used across the sales templates.
"""
from decimal import Decimal

from django import template

register = template.Library()


@register.filter(name='currency_bdt')
def currency_bdt(value):
    """
    Format a Decimal or numeric value as Bangladeshi Taka (৳).

    Displays with comma-separated thousands and two decimal places.
    Example: 1234.56 → '৳ 1,234.56'

    Args:
        value: A Decimal, float, or int to format.

    Returns:
        str: Formatted currency string prefixed with ৳.
    """
    try:
        value = Decimal(str(value))
    except (ValueError, TypeError):
        return '৳ 0.00'

    if value < 0:
        return f'−৳ {abs(value):,.2f}'

    return f'৳ {value:,.2f}'


@register.filter(name='unit_icon')
def unit_icon(unit):
    """
    Return a Bootstrap icon class string based on the medicine's unit type.

    Examples:
        'Pcs'   → 'bi-capsule' (pill icon)
        'Bottle' → 'bi-cup-straw'
        'Strip'  → 'bi-grid-3x2'
        'Box'    → 'bi-box'
        'Tube'   → 'bi-droplet'
        Default  → 'bi-box-seam'

    Args:
        unit: A string representing the medicine unit (e.g., 'Pcs', 'Bottle').

    Returns:
        str: Bootstrap Icons class name.
    """
    mapping = {
        'pcs': 'bi-capsule',
        'tablet': 'bi-capsule',
        'capsule': 'bi-capsule',
        'strip': 'bi-grid-3x2',
        'bottle': 'bi-cup-straw',
        'box': 'bi-box',
        'tube': 'bi-droplet',
        'vial': 'bi-eyedropper',
        'ampoule': 'bi-eyedropper',
        'syrup': 'bi-cup-straw',
        'suspension': 'bi-cup-straw',
        'drops': 'bi-eyedropper',
        'ointment': 'bi-droplet',
        'cream': 'bi-droplet',
        'gel': 'bi-droplet',
        'injection': 'bi-syringe',
        'sachet': 'bi-envelope-open',
        'pack': 'bi-box-seam',
        'set': 'bi-tools',
    }
    key = unit.strip().lower() if unit else ''
    return mapping.get(key, 'bi-capsule')