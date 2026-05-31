"""
MediPOS Inventory — URL Configuration.

Defines URL patterns for Batch (stock-in), StockLedger (audit trail),
and stock adjustment management.
"""
from django.urls import path

from . import views

app_name = 'inventory'

urlpatterns = [
    # ── Batch / Stock-In URLs ─────────────────────────────────────────────
    path(
        '',
        views.BatchListView.as_view(),
        name='batch_list',
    ),
    path(
        'batches/',
        views.BatchListView.as_view(),
        name='batch_list_alias',
    ),
    path(
        'stock-in/',
        views.StockInCreateView.as_view(),
        name='stock_in',
    ),
    path(
        'supplier-search/',
        views.SupplierSearchView.as_view(),
        name='supplier_search',
    ),
    path(
        'batches/<int:pk>/',
        views.BatchDetailView.as_view(),
        name='batch_detail',
    ),
    path(
        'batches/<int:pk>/edit/',
        views.BatchUpdateView.as_view(),
        name='batch_edit',
    ),

    # ── Stock Ledger / Audit Trail ────────────────────────────────────────
    path(
        'ledger/',
        views.StockLedgerListView.as_view(),
        name='stock_ledger_list',
    ),
    path(
        'ledger/medicine/<int:medicine_id>/',
        views.StockLedgerDetailListView.as_view(),
        name='stock_ledger_medicine',
    ),

    # ── Stock Adjustment ──────────────────────────────────────────────────
    path(
        'adjustment/',
        views.StockAdjustmentCreateView.as_view(),
        name='stock_adjustment',
    ),
]