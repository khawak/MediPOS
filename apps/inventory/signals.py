"""
MediPOS Inventory — Signals.

Django signal handlers that maintain data integrity between Batch,
StockLedger, and Medicine models by automatically updating stock
quantities and creating audit trail entries.
"""
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Batch, StockLedger


@receiver(post_save, sender=StockLedger)
def update_medicine_stock_quantity(sender, instance, created, **kwargs):
    """
    Update Medicine.stock_quantity when a StockLedger entry is created.

    This signal fires AFTER a StockLedger entry is saved (created=True only,
    not on updates). It recalculates the total stock for the medicine by
    summing all StockLedger quantities and updates the denormalized
    `stock_quantity` field on the Medicine model.

    Args:
        sender: The model class (StockLedger).
        instance: The StockLedger instance that was saved.
        created: True if a new record was created.
        **kwargs: Additional signal arguments.
    """
    if not created:
        return

    # Calculate total stock from all ledger entries for this medicine
    total = (
        StockLedger.objects
        .filter(medicine=instance.medicine)
        .aggregate(total=Sum('quantity'))['total']
    )
    total = total or 0

    # Ensure stock doesn't go below 0 (PositiveIntegerField constraint)
    if total < 0:
        total = 0

    # Update the medicine's stock_quantity directly to avoid recursive saves
    medicine = instance.medicine
    medicine.stock_quantity = total
    medicine.save(update_fields=['stock_quantity'])


@receiver(post_save, sender=Batch)
def create_stock_ledger_for_new_batch(sender, instance, created, **kwargs):
    """
    Auto-create a StockLedger IN entry when a new Batch is created.

    When a new Batch is saved for the first time (created=True), this signal
    automatically creates a corresponding StockLedger entry with type 'IN'
    to record the initial stock addition. This in turn triggers the
    `update_medicine_stock_quantity` signal, keeping Medicine.stock_quantity
    in sync.

    Args:
        sender: The model class (Batch).
        instance: The Batch instance that was saved.
        created: True if a new record was created.
        **kwargs: Additional signal arguments.
    """
    if not created:
        return

    supplier_name = instance.supplier.name if instance.supplier else 'Unknown'

    StockLedger.objects.create(
        medicine=instance.medicine,
        batch=instance,
        transaction_type='IN',
        quantity=instance.quantity,
        reference=f'Batch #{instance.batch_no}',
        note=f'Initial stock from {supplier_name}',
    )