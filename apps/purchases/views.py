"""
MediPOS Purchases / Procurement — Views.

Class-based views for the complete purchase order workflow:
DRAFT → ORDERED → RECEIVED (or CANCELLED). All views require
authentication; Admin & Pharmacist roles get full access via
StaffEditorMixin. Cashier users receive a 403 Forbidden.
"""

from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models, transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
    View,
)

from .filters import POFilter
from .forms import POReceiveForm, PurchaseOrderForm, PurchaseOrderItemForm
from .models import PurchaseOrder, PurchaseOrderItem, generate_po_number
from apps.inventory.models import Batch, StockLedger


# ═══════════════════════════════════════════════════════════════════════════════
# Mixins
# ═══════════════════════════════════════════════════════════════════════════════


class StaffEditorMixin(UserPassesTestMixin):
    """
    Mixin that restricts access to Admin and Pharmacist roles.

    Cashier users will receive a 403 Forbidden response with an error
    message and be redirected to the purchase order list.
    """

    def test_func(self):
        """Allow only Admin and Pharmacist roles."""
        user = self.request.user
        return user.is_authenticated and user.role in ('ADMIN', 'PHARMACIST')

    def handle_no_permission(self):
        """Show an error message and redirect to the PO list."""
        messages.error(
            self.request,
            _("You don't have permission to perform this action."),
        )
        return redirect('purchases:po_list')


# ═══════════════════════════════════════════════════════════════════════════════
# Purchase Order List View
# ═══════════════════════════════════════════════════════════════════════════════


class POListView(LoginRequiredMixin, ListView):
    """
    Display a paginated, filterable list of all purchase orders.

    Supports django-filter for status, supplier, date range, and
    search. Columns include PO#, Supplier, Date, Status badge,
    Items count, Total, and action buttons.

    All authenticated users can view the list; modifications require
    StaffEditorMixin on individual views.
    """

    model = PurchaseOrder
    template_name = 'purchases/po_list.html'
    context_object_name = 'purchase_orders'
    paginate_by = 25

    def get_queryset(self):
        """Apply POFilter and prefetch related supplier and items."""
        queryset = PurchaseOrder.objects.select_related(
            'supplier', 'created_by'
        ).prefetch_related('items').all()
        self.filterset = POFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        """Add the filterset to the template context."""
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset
        return context


# ═══════════════════════════════════════════════════════════════════════════════
# Purchase Order Create View
# ═══════════════════════════════════════════════════════════════════════════════


class POCreateView(LoginRequiredMixin, StaffEditorMixin, CreateView):
    """
    Create a new purchase order (header only — supplier, dates, notes).

    After creation, redirects to the PO detail page where line items can
    be added. The PO number is auto-generated on first save.

    Only Admin and Pharmacist users can create POs.
    """

    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'purchases/po_form.html'

    def form_valid(self, form):
        """
        Assign created_by, generate PO number, and redirect to detail.

        On successful form submission, sets the PO number, assigns the
        current user as creator, and displays a success message.
        """
        form.instance.created_by = self.request.user
        form.instance.po_number = generate_po_number()
        response = super().form_valid(form)
        messages.success(
            self.request,
            _('Purchase Order %(po)s created. Add items to complete it.')
            % {'po': self.object.po_number},
        )
        return response

    def get_context_data(self, **kwargs):
        """Indicate this is a create action and set the page title."""
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        context['page_title'] = _('New Purchase Order')
        return context


# ═══════════════════════════════════════════════════════════════════════════════
# Purchase Order Detail View
# ═══════════════════════════════════════════════════════════════════════════════


class PODetailView(LoginRequiredMixin, DetailView):
    """
    Display the full details of a purchase order including its line items.

    Shows PO info card, items table, status badge, and action buttons
    based on the current status:
        - DRAFT: Add Items, Edit, Send to Supplier, Cancel.
        - ORDERED: Receive Stock.
        - RECEIVED: Read-only with received info.
        - CANCELLED: Read-only.
    """

    model = PurchaseOrder
    template_name = 'purchases/po_detail.html'
    context_object_name = 'po'

    def get_object(self, queryset=None):
        """Fetch the purchase order or return a 404."""
        return get_object_or_404(PurchaseOrder, pk=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        """Add items (prefetched with medicine) to the template context."""
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.select_related('medicine').all()
        return context


# ═══════════════════════════════════════════════════════════════════════════════
# Purchase Order Update View
# ═══════════════════════════════════════════════════════════════════════════════


class POUpdateView(LoginRequiredMixin, StaffEditorMixin, UpdateView):
    """
    Edit a purchase order's header fields.

    Only POs in DRAFT status can be edited. Once ordered/received/cancelled,
    the PO is immutable. Redirects to PO detail on success.
    """

    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'purchases/po_form.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Check that the PO is still in DRAFT status before allowing edits.

        If not DRAFT, shows an error and redirects to the detail view.
        """
        self.object = self.get_object()
        if self.object.status != 'DRAFT':
            messages.error(
                request,
                _('Only draft purchase orders can be edited.'),
            )
            return redirect(self.object.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Add a success message after updating the PO."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            _('Purchase Order %(po)s updated successfully.')
            % {'po': self.object.po_number},
        )
        return response

    def get_context_data(self, **kwargs):
        """Indicate this is an edit action and set the page title."""
        context = super().get_context_data(**kwargs)
        context['action'] = 'Edit'
        context['page_title'] = _('Edit %(po)s') % {'po': self.object.po_number}
        return context


# ═══════════════════════════════════════════════════════════════════════════════
# Purchase Order Cancel View
# ═══════════════════════════════════════════════════════════════════════════════


class POCancelView(LoginRequiredMixin, StaffEditorMixin, View):
    """
    Cancel a purchase order by setting its status to CANCELLED.

    Only POs in DRAFT or ORDERED status can be cancelled. Once received,
    a PO cannot be cancelled. This is a POST-only view for safety.
    """

    def post(self, request, *args, **kwargs):
        """
        Set the PO status to CANCELLED and redirect to detail.

        Validates that the PO is not already RECEIVED before cancelling.
        """
        po = get_object_or_404(PurchaseOrder, pk=kwargs.get('pk'))
        if po.status == 'RECEIVED':
            messages.error(
                request,
                _('Cannot cancel a purchase order that has already been received.'),
            )
            return redirect(po.get_absolute_url())
        po.status = 'CANCELLED'
        po.save(update_fields=['status', 'updated_at'])
        messages.warning(
            request,
            _('Purchase Order %(po)s has been cancelled.')
            % {'po': po.po_number},
        )
        return redirect(po.get_absolute_url())


# ═══════════════════════════════════════════════════════════════════════════════
# Send to Supplier View
# ═══════════════════════════════════════════════════════════════════════════════


class POSendToSupplierView(LoginRequiredMixin, StaffEditorMixin, View):
    """
    Send a draft purchase order to the supplier by changing status to ORDERED.

    Sets the order_date to today and updates the status. Only valid for
    POs currently in DRAFT status.
    """

    def post(self, request, *args, **kwargs):
        """
        Set the PO status to ORDERED and order_date to today.

        Validates that the PO has at least one item before sending.
        """
        po = get_object_or_404(PurchaseOrder, pk=kwargs.get('pk'))
        if po.status != 'DRAFT':
            messages.error(
                request,
                _('Only draft purchase orders can be sent.'),
            )
            return redirect(po.get_absolute_url())
        if po.items_count == 0:
            messages.error(
                request,
                _('Add at least one item before sending the purchase order.'),
            )
            return redirect(po.get_absolute_url())
        po.status = 'ORDERED'
        po.order_date = date.today()
        po.save(update_fields=['status', 'order_date', 'updated_at'])
        messages.success(
            request,
            _('Purchase Order %(po)s has been sent to %(supplier)s.')
            % {'po': po.po_number, 'supplier': po.supplier.name},
        )
        return redirect(po.get_absolute_url())


# ═══════════════════════════════════════════════════════════════════════════════
# Add Item to Purchase Order View
# ═══════════════════════════════════════════════════════════════════════════════


class POAddItemView(LoginRequiredMixin, StaffEditorMixin, CreateView):
    """
    Add a line item to an existing purchase order.

    The purchase_order FK is pre-filled from the URL pk parameter.
    Only DRAFT POs can have items added. On success, redirects back
    to the PO detail view.
    """

    model = PurchaseOrderItem
    form_class = PurchaseOrderItemForm
    template_name = 'purchases/po_item_form.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Resolve the parent PO and validate it's in DRAFT status.

        If not DRAFT, shows an error and redirects to detail.
        """
        self.purchase_order = get_object_or_404(
            PurchaseOrder, pk=self.kwargs.get('pk')
        )
        if self.purchase_order.status != 'DRAFT':
            messages.error(
                request,
                _('Items can only be added to draft purchase orders.'),
            )
            return redirect(self.purchase_order.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """
        Attach the item to the parent PO and show a success message.

        The item's save() method automatically recalculates the PO's
        total_amount via the PurchaseOrderItem.save() override.
        """
        form.instance.purchase_order = self.purchase_order
        response = super().form_valid(form)
        messages.success(
            self.request,
            _('%(medicine)s x%(qty)d added to %(po)s.')
            % {
                'medicine': self.object.medicine.name,
                'qty': self.object.quantity,
                'po': self.purchase_order.po_number,
            },
        )
        return response

    def get_success_url(self):
        """Redirect back to the parent PO detail after adding an item."""
        return self.purchase_order.get_absolute_url()

    def get_context_data(self, **kwargs):
        """Add the parent PO to the template context."""
        context = super().get_context_data(**kwargs)
        context['po'] = self.purchase_order
        return context


# ═══════════════════════════════════════════════════════════════════════════════
# Delete Item from Purchase Order View
# ═══════════════════════════════════════════════════════════════════════════════


class PODeleteItemView(LoginRequiredMixin, StaffEditorMixin, DeleteView):
    """
    Delete a line item from a purchase order.

    Only items belonging to DRAFT POs can be deleted. After deletion,
    the parent PO's total_amount is recalculated automatically via the
    PurchaseOrderItem's save/delete signals.

    Redirects back to the PO detail view on success.
    """

    model = PurchaseOrderItem
    template_name = 'purchases/po_item_confirm_delete.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Resolve the item, validate parent PO is DRAFT, then proceed.

        If the parent PO is not DRAFT, shows an error and redirects.
        """
        self.item = get_object_or_404(PurchaseOrderItem, pk=kwargs.get('pk'))
        if self.item.purchase_order.status != 'DRAFT':
            messages.error(
                request,
                _('Items can only be deleted from draft purchase orders.'),
            )
            return redirect(self.item.purchase_order.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """Return to the parent PO detail after deleting the item."""
        return self.item.purchase_order.get_absolute_url()

    def get_context_data(self, **kwargs):
        """Add the parent PO context for the confirmation template."""
        context = super().get_context_data(**kwargs)
        context['po'] = self.item.purchase_order
        return context

    def form_valid(self, form):
        """
        Delete the item and recalculate the parent PO's total.

        The PO total is recalculated via the PurchaseOrderItem's delete
        behavior. A success message is displayed.
        """
        po = self.item.purchase_order
        po_number = po.po_number
        medicine_name = self.item.medicine.name
        response = super().form_valid(form)
        # Recalculate PO total after item deletion
        po.total_amount = po.items.aggregate(
            total=models.Sum('line_total')
        )['total'] or 0.00
        po.save(update_fields=['total_amount'])
        messages.success(
            self.request,
            _('%(medicine)s removed from %(po)s.')
            % {'medicine': medicine_name, 'po': po_number},
        )
        return response


# Need to import Sum here for PODeleteItemView
from django.db.models import Sum  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════════
# Receive Purchase Order View (THE KEY VIEW)
# ═══════════════════════════════════════════════════════════════════════════════


class POReceiveView(LoginRequiredMixin, StaffEditorMixin, FormView):
    """
    Receive stock for a purchase order — the most important procurement view.

    GET: Shows the POReceiveForm with a summary of the PO being received.
    POST: For each PO item, creates a Batch record which triggers the
          existing signal chain:
              Batch post_save → StockLedger IN → Medicine.stock_quantity update

    The entire operation is wrapped in transaction.atomic() to ensure
    all-or-nothing behavior. On success, the PO status is set to RECEIVED
    and the receiving user is recorded.

    Only ORDERED POs can be received.
    """

    template_name = 'purchases/po_receive.html'
    form_class = POReceiveForm

    def dispatch(self, request, *args, **kwargs):
        """
        Resolve the PO and validate it's in ORDERED status.

        If the PO is not ORDERED, shows an error and redirects to detail.
        """
        self.purchase_order = get_object_or_404(
            PurchaseOrder, pk=self.kwargs.get('pk')
        )
        if self.purchase_order.status != 'ORDERED':
            messages.error(
                request,
                _('Only ordered purchase orders can be received.'),
            )
            return redirect(self.purchase_order.get_absolute_url())
        if self.purchase_order.items_count == 0:
            messages.error(
                request,
                _('Cannot receive a purchase order with no items.'),
            )
            return redirect(self.purchase_order.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add the PO and its items to the template context."""
        context = super().get_context_data(**kwargs)
        context['po'] = self.purchase_order
        context['items'] = self.purchase_order.items.select_related(
            'medicine'
        ).all()
        return context

    @transaction.atomic
    def form_valid(self, form):
        """
        Create Batch records for each PO item and finalize the receipt.

        For each purchase order item:
        1. Creates a Batch with the item's medicine, supplier, quantity, etc.
        2. The Batch post_save signal auto-creates a StockLedger IN entry.
        3. The StockLedger post_save signal auto-updates medicine stock.

        Then sets PO status to RECEIVED and records the receiving user.

        Args:
            form: The validated POReceiveForm with received_by and notes.

        Returns:
            HttpResponseRedirect to the PO detail page.
        """
        po = self.purchase_order
        received_by = form.cleaned_data['received_by']
        receiving_notes = form.cleaned_data.get('notes', '')

        # Default expiry: 1 year from today if not specified
        default_expiry = date.today() + timedelta(days=365)

        for item in po.items.all():
            batch_no = item.batch_no or f'{po.po_number}-{item.medicine.id}'
            expiry = item.expiry_date or default_expiry

            Batch.objects.create(
                medicine=item.medicine,
                supplier=po.supplier,
                batch_no=batch_no,
                expiry_date=expiry,
                quantity=item.quantity,
                purchase_price=item.unit_price,
                purchase_order=po.po_number,
            )

        # Update PO status
        po.status = 'RECEIVED'
        po.received_by = received_by
        if receiving_notes:
            existing = po.notes or ''
            po.notes = (existing + '\n' + receiving_notes).strip()
        po.save(update_fields=['status', 'received_by', 'notes', 'updated_at'])

        messages.success(
            self.request,
            _('PO %(po)s received successfully. Stock updated — '
              '%(count)d batches created.')
            % {'po': po.po_number, 'count': po.items_count},
        )

        # ── Auto-update supplier balance (negative = we owe supplier) ──
        # When we receive stock, we now owe the supplier the PO total
        supplier = po.supplier
        if supplier:
            supplier.balance -= po.total_amount
            supplier.save(update_fields=['balance', 'updated_at'])

        return HttpResponseRedirect(po.get_absolute_url())


# ═══════════════════════════════════════════════════════════════════════════════
# Purchase Return View
# ═══════════════════════════════════════════════════════════════════════════════


class POPurchaseReturnView(LoginRequiredMixin, StaffEditorMixin, View):
    """
    Record a purchase return for a specific PO item.

    Creates a StockLedger entry with transaction_type='RET' and negative
    quantity. The existing signal chain auto-updates Medicine.stock_quantity.
    Notes the return details in the PO notes field.

    Expects POST with item_id and return_quantity.
    """

    def post(self, request, *args, **kwargs):
        """
        Process a purchase return for a specific item.

        Validates the return quantity, creates a StockLedger RET entry,
        and appends return details to the PO notes.

        Args:
            request: The HTTP request containing item_id and return_quantity.
            kwargs: URL parameters including pk (PO id).

        Returns:
            HttpResponseRedirect to the PO detail page.
        """
        po = get_object_or_404(PurchaseOrder, pk=kwargs.get('pk'))

        if po.status != 'RECEIVED':
            messages.error(
                request,
                _('Returns can only be processed for received purchase orders.'),
            )
            return redirect(po.get_absolute_url())

        item_id = request.POST.get('item_id')
        return_quantity_str = request.POST.get('return_quantity', '0')

        try:
            return_quantity = int(return_quantity_str)
        except (ValueError, TypeError):
            messages.error(request, _('Invalid return quantity.'))
            return redirect(po.get_absolute_url())

        item = get_object_or_404(PurchaseOrderItem, pk=item_id)

        if return_quantity <= 0 or return_quantity > item.quantity:
            messages.error(
                request,
                _('Return quantity must be between 1 and %(max)d.')
                % {'max': item.quantity},
            )
            return redirect(po.get_absolute_url())

        # Create StockLedger RET entry (negative quantity)
        StockLedger.objects.create(
            medicine=item.medicine,
            transaction_type='RET',
            quantity=-return_quantity,
            reference=f'PO Return: {po.po_number}',
            note=f'Returned {return_quantity} units of {item.medicine.name}',
            created_by=request.user,
        )

        # Append return info to PO notes
        return_note = (
            f'[RETURN] {item.medicine.name}: {return_quantity} units '
            f'returned by {request.user} on {date.today()}'
        )
        existing = po.notes or ''
        po.notes = (existing + '\n' + return_note).strip()
        po.save(update_fields=['notes', 'updated_at'])

        messages.success(
            request,
            _('%(qty)d units of %(medicine)s returned successfully.')
            % {'qty': return_quantity, 'medicine': item.medicine.name},
        )

        return redirect(po.get_absolute_url())


# ═══════════════════════════════════════════════════════════════════════════════
# Purchase Order Print View
# ═══════════════════════════════════════════════════════════════════════════════


class POPrintView(LoginRequiredMixin, DetailView):
    """
    Print-friendly view of a purchase order.

    Renders the PO on a clean A4-ready template that auto-triggers the
    browser's print dialog on load. All users can print POs.

    The template includes @media print CSS to hide the sidebar, navbar,
    and action buttons, leaving only the PO content.
    """

    model = PurchaseOrder
    template_name = 'purchases/po_print.html'
    context_object_name = 'po'

    def get_object(self, queryset=None):
        """Fetch the purchase order or return a 404."""
        return get_object_or_404(PurchaseOrder, pk=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        """Add line items (prefetched with medicine) to the context."""
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.select_related('medicine').all()
        return context