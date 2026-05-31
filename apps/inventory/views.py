"""
MediPOS Inventory — Views.

Class-based views for Batch (stock-in), StockLedger (audit trail),
and stock adjustments. All views require authentication; Admin &
Pharmacist get full access, Cashier is read-only.
"""
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)

from .filters import BatchFilter, StockLedgerFilter
from .forms import StockAdjustmentForm, StockInForm
from .models import Batch, StockLedger
from apps.medicines.models import Medicine
from apps.suppliers.models import Supplier


# ═══════════════════════════════════════════════════════════════════════════════
# Mixins
# ═══════════════════════════════════════════════════════════════════════════════


class StaffEditorMixin(UserPassesTestMixin):
    """
    Mixin that restricts access to Admin and Pharmacist roles.

    Cashier users will receive a 403 Forbidden response with an error message
    and be redirected to the inventory batch list.
    """

    def test_func(self):
        """Allow only Admin and Pharmacist roles."""
        user = self.request.user
        return user.is_authenticated and user.role in ('ADMIN', 'PHARMACIST')

    def handle_no_permission(self):
        """Show an error message and redirect to the batch list."""
        messages.error(
            self.request,
            _("You don't have permission to perform this action."),
        )
        return redirect('inventory:batch_list')


class AdminOnlyMixin(UserPassesTestMixin):
    """
    Mixin that restricts access to Admin role only.

    Pharmacist and Cashier users will receive a 403 Forbidden response
    with an error message and be redirected to the inventory batch list.
    """

    def test_func(self):
        """Allow only Admin role."""
        user = self.request.user
        return user.is_authenticated and user.role == 'ADMIN'

    def handle_no_permission(self):
        """Show an error message and redirect to the batch list."""
        messages.error(
            self.request,
            _("Only administrators can perform this action."),
        )
        return redirect('inventory:batch_list')


# ═══════════════════════════════════════════════════════════════════════════════
# Batch / Stock-In Views
# ═══════════════════════════════════════════════════════════════════════════════


class BatchListView(LoginRequiredMixin, ListView):
    """
    Display a paginated, filterable list of all batches (main inventory view).

    Supports django-filter for search, supplier, expiry status, and active
    toggle. Also shows summary stats: total batches, expiring within 30 days,
    expiring within 60 days, and expired.
    """

    model = Batch
    template_name = 'inventory/batch_list.html'
    context_object_name = 'batches'
    paginate_by = 25

    def get_queryset(self):
        """Apply batch filters from the BatchFilter FilterSet."""
        queryset = Batch.objects.select_related(
            'medicine', 'supplier'
        ).all()
        self.filterset = BatchFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        """Add filterset and expiry summary stats to the template context."""
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset

        today = date.today()
        all_batches = Batch.objects.filter(is_active=True)

        context['stats'] = {
            'total': all_batches.count(),
            'expired': all_batches.filter(expiry_date__lt=today).count(),
            'expiring_30': all_batches.filter(
                expiry_date__gte=today,
                expiry_date__lte=today + date.resolution * 30,
            ).count(),
            'expiring_60': all_batches.filter(
                expiry_date__gte=today,
                expiry_date__lte=today + date.resolution * 60,
            ).count(),
        }
        return context


class StockInCreateView(LoginRequiredMixin, StaffEditorMixin, CreateView):
    """
    Create a new Batch (stock-in operation).

    On successful form submission, saving the Batch triggers a signal chain:
    Batch save → creates StockLedger IN entry → updates Medicine.stock_quantity.

    Displays a success message and redirects to the batch list.
    """

    model = Batch
    form_class = StockInForm
    template_name = 'inventory/stock_in_form.html'
    success_url = reverse_lazy('inventory:batch_list')

    def form_valid(self, form):
        """Add a success message after creating the batch/stock-in."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            _('Stock-in recorded: %(medicine)s — Batch %(batch)s (%(qty)d units).')
            % {
                'medicine': self.object.medicine.name,
                'batch': self.object.batch_no,
                'qty': self.object.quantity,
            },
        )
        return response


class BatchDetailView(LoginRequiredMixin, DetailView):
    """
    Display the full details of a single batch.

    Shows batch info (medicine, supplier, expiry, quantity) and all related
    StockLedger entries for this batch.
    """

    model = Batch
    template_name = 'inventory/batch_detail.html'
    context_object_name = 'batch'

    def get_object(self, queryset=None):
        """Fetch the batch or return a 404."""
        return get_object_or_404(Batch, pk=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        """Add related stock ledger entries to the context."""
        context = super().get_context_data(**kwargs)
        context['ledger_entries'] = self.object.stock_ledger.select_related(
            'medicine', 'created_by'
        ).all()
        return context


class BatchUpdateView(LoginRequiredMixin, AdminOnlyMixin, UpdateView):
    """
    Edit an existing batch record (Admin only).

    Allows admins to update batch metadata: batch_no, manufacture_date,
    expiry_date, quantity, purchase_price, purchase_order, and active status.
    On success, updates the associated StockLedger IN entry to reflect
    any quantity changes, then recalculates Medicine.stock_quantity.
    """

    model = Batch
    form_class = StockInForm
    template_name = 'inventory/stock_in_form.html'
    success_url = reverse_lazy('inventory:batch_list')

    def get_object(self, queryset=None):
        """Fetch the batch or return a 404."""
        return get_object_or_404(Batch, pk=self.kwargs.get('pk'))

    def get_form(self, form_class=None):
        """Pre-populate the form with the batch's existing data."""
        form = super().get_form(form_class)
        # When editing, show the current medicine in the dropdown
        return form

    def form_valid(self, form):
        """Update the batch and sync the related StockLedger entry."""
        batch = form.save(commit=False)
        # Detect quantity change before saving
        old_qty = Batch.objects.get(pk=batch.pk).quantity
        qty_diff = batch.quantity - old_qty

        response = super().form_valid(form)

        if qty_diff != 0:
            # Update the original StockLedger IN entry to reflect new quantity
            original_ledger = StockLedger.objects.filter(
                batch=batch,
                transaction_type='IN',
            ).first()
            if original_ledger:
                original_ledger.quantity = batch.quantity
                original_ledger.save(update_fields=['quantity'])

            # Manually recalculate medicine stock since the signal only
            # fires on created=True, not on updates
            total = (
                StockLedger.objects
                .filter(medicine=batch.medicine)
                .aggregate(total=Sum('quantity'))['total']
            ) or 0
            if total < 0:
                total = 0
            batch.medicine.stock_quantity = total
            batch.medicine.save(update_fields=['stock_quantity'])

        messages.success(
            self.request,
            _('Batch #%(batch)s updated successfully.') % {'batch': batch.batch_no},
        )
        return response

    def get_context_data(self, **kwargs):
        """Mark the form as editing an existing batch."""
        context = super().get_context_data(**kwargs)
        context['editing_batch'] = True
        context['batch'] = self.object
        return context


# ═══════════════════════════════════════════════════════════════════════════════
# Stock Ledger / Adjustment Views
# ═══════════════════════════════════════════════════════════════════════════════


class StockLedgerListView(LoginRequiredMixin, ListView):
    """
    Display a paginated, filterable list of all stock ledger entries.

    Supports django-filter for medicine, transaction type, and date range.
    Columns include: date, medicine, type (colored badge), quantity,
    reference, and created_by.
    """

    model = StockLedger
    template_name = 'inventory/stock_ledger_list.html'
    context_object_name = 'ledger_entries'
    paginate_by = 25

    def get_queryset(self):
        """Apply stock ledger filters from the StockLedgerFilter FilterSet."""
        queryset = StockLedger.objects.select_related(
            'medicine', 'batch', 'created_by'
        ).all()
        self.filterset = StockLedgerFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        """Add filterset to the template context."""
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset
        return context


class StockAdjustmentCreateView(LoginRequiredMixin, StaffEditorMixin, FormView):
    """
    Create a manual stock adjustment (deduction from inventory).

    GET: Renders the StockAdjustmentForm.
    POST: Creates a StockLedger entry with transaction_type='ADJ' and
          negative quantity. The signal chain auto-updates
          Medicine.stock_quantity.
    """

    template_name = 'inventory/stock_adjustment_form.html'
    form_class = StockAdjustmentForm
    success_url = reverse_lazy('inventory:batch_list')

    def form_valid(self, form):
        """
        Create a StockLedger ADJ entry with negative quantity.

        The post_save signal on StockLedger will automatically update
        the medicine's stock_quantity.
        """
        medicine = form.cleaned_data['medicine']
        adj_type = form.cleaned_data['adjustment_type']
        quantity = form.cleaned_data['quantity']
        reason = form.cleaned_data['reason']

        adj_type_display = dict(StockAdjustmentForm.ADJUSTMENT_TYPES).get(
            adj_type, adj_type
        )

        StockLedger.objects.create(
            medicine=medicine,
            transaction_type='ADJ',
            quantity=-quantity,  # Negative for deduction
            reference=f'Adjustment: {adj_type_display}',
            note=reason,
            created_by=self.request.user,
        )

        messages.success(
            self.request,
            _('Stock adjustment recorded: %(medicine)s — '
              '%(qty)d units deducted (%(type)s).')
            % {
                'medicine': medicine.name,
                'qty': quantity,
                'type': adj_type_display,
            },
        )
        return super().form_valid(form)


class StockLedgerDetailListView(LoginRequiredMixin, ListView):
    """
    Display all stock ledger entries for a specific medicine.

    Filtered by the medicine_id URL parameter. Shows the medicine's name
    and current stock quantity in the header.
    """

    model = StockLedger
    template_name = 'inventory/stock_ledger_medicine.html'
    context_object_name = 'ledger_entries'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        """Resolve the medicine before dispatching."""
        self.medicine = get_object_or_404(Medicine, pk=self.kwargs.get('medicine_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Filter ledger entries to this medicine only."""
        return StockLedger.objects.filter(
            medicine=self.medicine
        ).select_related('batch', 'created_by').order_by('-created_at')

    def get_context_data(self, **kwargs):
        """Add the medicine object to the context."""
        context = super().get_context_data(**kwargs)
        context['medicine'] = self.medicine
        return context


# ═══════════════════════════════════════════════════════════════════════════════
# AJAX Search Views
# ═══════════════════════════════════════════════════════════════════════════════


class SupplierSearchView(LoginRequiredMixin, View):
    """
    Search active suppliers via GET for the stock-in form's supplier field.

    Query param 'q' searches across supplier name and contact person.
    Returns a JSON list of matching active suppliers.
    """

    def get(self, request):
        """Search and return matching suppliers as JSON."""
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'success': True, 'suppliers': []})

        suppliers = Supplier.objects.filter(is_active=True).filter(
            Q(name__icontains=query)
            | Q(contact_person__icontains=query)
        )[:20]

        results = []
        for s in suppliers:
            results.append({
                'id': s.pk,
                'name': s.name,
                'contact_person': s.contact_person or '',
                'phone': s.phone,
            })

        return JsonResponse({'success': True, 'suppliers': results})