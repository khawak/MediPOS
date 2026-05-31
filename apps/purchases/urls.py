"""
MediPOS Purchases / Procurement — URL Configuration.

Defines URL patterns for the complete purchase order workflow:
listing, creating, editing, sending to supplier, receiving stock,
managing items, and purchase returns.
"""

from django.urls import path

from . import views

app_name = 'purchases'

urlpatterns = [
    # ── Purchase Order Listing ───────────────────────────────────────────
    path(
        '',
        views.POListView.as_view(),
        name='po_list',
    ),

    # ── Create Purchase Order ────────────────────────────────────────────
    path(
        'add/',
        views.POCreateView.as_view(),
        name='po_create',
    ),

    # ── Purchase Order Detail ────────────────────────────────────────────
    path(
        '<int:pk>/',
        views.PODetailView.as_view(),
        name='po_detail',
    ),

    # ── Edit Purchase Order (DRAFT only) ─────────────────────────────────
    path(
        '<int:pk>/edit/',
        views.POUpdateView.as_view(),
        name='po_edit',
    ),

    # ── Cancel Purchase Order ────────────────────────────────────────────
    path(
        '<int:pk>/cancel/',
        views.POCancelView.as_view(),
        name='po_cancel',
    ),

    # ── Send to Supplier (DRAFT → ORDERED) ───────────────────────────────
    path(
        '<int:pk>/send/',
        views.POSendToSupplierView.as_view(),
        name='po_send',
    ),

    # ── Add Item to Purchase Order ───────────────────────────────────────
    path(
        '<int:pk>/add-item/',
        views.POAddItemView.as_view(),
        name='po_add_item',
    ),

    # ── Delete Item from Purchase Order ──────────────────────────────────
    path(
        'item/<int:pk>/delete/',
        views.PODeleteItemView.as_view(),
        name='po_delete_item',
    ),

    # ── Receive Purchase Order (ORDERED → RECEIVED) ─────────────────────
    path(
        '<int:pk>/receive/',
        views.POReceiveView.as_view(),
        name='po_receive',
    ),

    # ── Print Purchase Order ──────────────────────────────────────────
    path(
        '<int:pk>/print/',
        views.POPrintView.as_view(),
        name='po_print',
    ),

    # ── Purchase Return ──────────────────────────────────────────────────
    path(
        '<int:pk>/return/',
        views.POPurchaseReturnView.as_view(),
        name='po_return',
    ),
]