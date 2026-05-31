"""
MediPOS Returns & Refunds — Views.

Class-based views for the sales return and refund workflow:
- List all returns with search by invoice number.
- Create a return (lookup sale → select items → process with restock).
- View return details.

Admin & Pharmacist can process returns; Cashier gets read-only access.
"""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, ListView

from apps.inventory.models import Batch, StockLedger
from apps.sales.models import Sale, SaleItem

from .forms import ReturnItemsForm, SalesReturnForm
from .models import SalesReturn, SalesReturnItem


# ═══════════════════════════════════════════════════════════════════════════════
# Mixins
# ═══════════════════════════════════════════════════════════════════════════════


class StaffEditorMixin(UserPassesTestMixin):
    """
    Mixin that restricts access to Admin and Pharmacist roles.

    Cashier users will receive a 403 Forbidden response with an error
    message and be redirected to the returns list.
    """

    def test_func(self):
        """Allow only Admin and Pharmacist roles."""
        user = self.request.user
        return user.is_authenticated and user.role in ('ADMIN', 'PHARMACIST')

    def handle_no_permission(self):
        """Show an error message and redirect to the returns list."""
        messages.error(
            self.request,
            _("You don't have permission to perform this action."),
        )
        return redirect('returns:sales_return_list')


# ═══════════════════════════════════════════════════════════════════════════════
# Sales Return List View
# ═══════════════════════════════════════════════════════════════════════════════


class SalesReturnListView(LoginRequiredMixin, ListView):
    """
    Display a paginated, searchable list of all sales returns.

    Supports search by sale invoice number. All authenticated users
    can view the list; creating returns requires StaffEditorMixin.
    """

    model = SalesReturn
    template_name = 'returns/sales_return_list.html'
    context_object_name = 'returns'
    paginate_by = 25

    def get_queryset(self):
        """
        Apply optional search filter by sale invoice number.

        Returns:
            QuerySet: Filtered SalesReturn queryset with related prefetching.
        """
        queryset = SalesReturn.objects.select_related(
            'sale', 'processed_by',
        ).prefetch_related('items').all()

        search = self.request.GET.get('q', '').strip()
        if search:
            queryset = queryset.filter(sale__invoice_no__icontains=search)

        return queryset

    def get_context_data(self, **kwargs):
        """Add the search query value to template context."""
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


# ═══════════════════════════════════════════════════════════════════════════════
# Sales Return Create View
# ═══════════════════════════════════════════════════════════════════════════════


class SalesReturnCreateView(LoginRequiredMixin, StaffEditorMixin, FormView):
    """
    Multi-step view for processing a sales return.

    Flow:
        1. GET: Show the invoice lookup form (SalesReturnForm).
        2. POST (lookup): Validate the invoice, then show the return items
           selection form (ReturnItemsForm) alongside the sale summary.
        3. POST (process): Process the return — create SalesReturn with
           SalesReturnItem entries, create StockLedger RET entries for
           restock, and update the Sale status.

    The entire processing step is wrapped in transaction.atomic() for
    data integrity.
    """

    template_name = 'returns/sales_return_form.html'
    form_class = SalesReturnForm

    def get_context_data(self, **kwargs):
        """
        Add step tracking, sale data, and return items form to context.

        If a sale has been looked up (stored in session), builds the
        ReturnItemsForm and sale summary for rendering.
        """
        context = super().get_context_data(**kwargs)

        sale_id = self.request.session.get('return_sale_id')
        if sale_id:
            try:
                sale = Sale.objects.prefetch_related(
                    'items__medicine', 'items__batch',
                ).get(pk=sale_id)
                context['sale'] = sale
                context['step'] = 'select_items'

                # Build the return items form (unbound or with POST data)
                if self.request.method == 'POST':
                    context['items_form'] = ReturnItemsForm(
                        sale=sale, data=self.request.POST,
                    )
                else:
                    context['items_form'] = ReturnItemsForm(sale=sale)
            except Sale.DoesNotExist:
                # Session has stale sale_id; clear it
                self.request.session.pop('return_sale_id', None)
                context['step'] = 'lookup'
        else:
            context['step'] = 'lookup'

        return context

    def form_valid(self, form):
        """
        Handle form submission based on the current step.

        Step 1 (lookup): Store the resolved sale ID in the session
        and return to the same page to show the items form.

        Step 2 (process): The ReturnItemsForm is validated separately
        in post(). If valid, process the return with transaction.atomic().

        Args:
            form: The validated SalesReturnForm (invoice lookup).

        Returns:
            HttpResponse: Redirect to return detail or re-render with errors.
        """
        # Check if this is the lookup step or the processing step
        process = self.request.POST.get('process_return', '')

        if process == '1':
            # This is the processing step — handled via process_return()
            return self.process_return()

        # This is the lookup step — store sale and show items form
        sale = form.sale
        self.request.session['return_sale_id'] = sale.pk
        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        """
        Override post to handle both the lookup form and the process action.

        If 'process_return' is in POST data, validates the ReturnItemsForm
        and processes the return. Otherwise, delegates to the standard
        FormView post for invoice lookup.
        """
        process = request.POST.get('process_return', '')

        if process == '1':
            return self.process_return()

        return super().post(request, *args, **kwargs)

    def process_return(self):
        """
        Validate the ReturnItemsForm and process the return.

        Creates SalesReturn, SalesReturnItem entries, StockLedger RET
        entries (positive quantity → restock), and updates Sale status.
        All wrapped in transaction.atomic().

        Returns:
            HttpResponseRedirect: Redirect to the return detail page on success.
            HttpResponse: Re-render with errors on validation failure.
        """
        sale_id = self.request.session.get('return_sale_id')
        if not sale_id:
            messages.error(self.request, _('No sale selected. Please start over.'))
            return redirect('returns:sales_return_create')

        sale = get_object_or_404(Sale, pk=sale_id)

        # Validate the items form
        items_form = ReturnItemsForm(sale=sale, data=self.request.POST)
        if not items_form.is_valid():
            return self.render_to_response(
                self.get_context_data(
                    form=SalesReturnForm(initial={'invoice_no': sale.invoice_no}),
                )
            )

        selected_items = items_form.selected_items
        refund_amount = items_form.refund_amount
        reason = self.request.POST.get('reason', '').strip()

        if not reason:
            messages.error(self.request, _('Please provide a reason for the return.'))
            return self.render_to_response(
                self.get_context_data(
                    form=SalesReturnForm(initial={'invoice_no': sale.invoice_no}),
                )
            )

        try:
            with transaction.atomic():
                # Create the SalesReturn record
                sales_return = SalesReturn.objects.create(
                    sale=sale,
                    refund_amount=refund_amount,
                    reason=reason,
                    processed_by=self.request.user,
                    notes=self.request.POST.get('notes', '').strip(),
                )

                # Create SalesReturnItem entries and StockLedger restock entries
                for item_data in selected_items:
                    sale_item = item_data['sale_item']
                    qty = item_data['quantity']
                    unit_price = item_data['unit_price']

                    # Create the return line item
                    SalesReturnItem.objects.create(
                        sales_return=sales_return,
                        sale_item=sale_item,
                        quantity=qty,
                        unit_price=unit_price,
                    )

                    # Restore batch quantity
                    if sale_item.batch:
                        sale_item.batch.quantity += qty
                        sale_item.batch.save(update_fields=['quantity'])

                    # Create StockLedger RET entry (positive quantity = restock)
                    # The existing signal auto-updates Medicine.stock_quantity
                    StockLedger.objects.create(
                        medicine=sale_item.medicine,
                        batch=sale_item.batch,
                        transaction_type='RET',
                        quantity=qty,  # Positive → restock
                        reference=f'Return: {sale.invoice_no}',
                        note=(
                            f'Return: {qty} x {sale_item.medicine.name} '
                            f'(Invoice: {sale.invoice_no}) — {reason}'
                        ),
                        created_by=self.request.user,
                    )

                # Update Sale status
                # Determine if all items were returned (fully refunded)
                original_total_qty = sale.items.aggregate(
                    total=Sum('quantity')
                )['total'] or 0

                returned_total_qty = sum(
                    item['quantity'] for item in selected_items
                )

                # Also account for any previous returns
                previous_returned = SalesReturnItem.objects.filter(
                    sale_item__sale=sale,
                ).exclude(
                    sales_return=sales_return,
                ).aggregate(
                    total=Sum('quantity')
                )['total'] or 0

                total_ever_returned = returned_total_qty + previous_returned

                if total_ever_returned >= original_total_qty:
                    sale.status = Sale.Status.REFUNDED
                # else leave as COMPLETED for partial return
                sale.save(update_fields=['status', 'updated_at'])

            # Clear session after successful processing
            self.request.session.pop('return_sale_id', None)

            messages.success(
                self.request,
                _(
                    'Return processed successfully! Refund amount: ৳%(amount)s. '
                    'Stock has been restocked.'
                )
                % {'amount': f'{refund_amount:,.2f}'},
            )
            return redirect(sales_return.get_absolute_url())

        except Exception as e:
            messages.error(
                self.request,
                _('An error occurred while processing the return: %(error)s')
                % {'error': str(e)},
            )
            return self.render_to_response(
                self.get_context_data(
                    form=SalesReturnForm(initial={'invoice_no': sale.invoice_no}),
                )
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Sales Return Detail View
# ═══════════════════════════════════════════════════════════════════════════════


class SalesReturnDetailView(LoginRequiredMixin, DetailView):
    """
    Display the full details of a sales return transaction.

    Shows return metadata (date, reason, refund amount, processor),
    the original sale info, and a table of returned items.
    """

    model = SalesReturn
    template_name = 'returns/sales_return_detail.html'
    context_object_name = 'return_obj'

    def get_object(self, queryset=None):
        """Fetch the SalesReturn with all related data prefetched."""
        return get_object_or_404(
            SalesReturn.objects.select_related(
                'sale__customer', 'processed_by',
            ).prefetch_related(
                'items__sale_item__medicine',
            ),
            pk=self.kwargs.get('pk'),
        )

    def get_context_data(self, **kwargs):
        """Add the original sale to the context for linking."""
        context = super().get_context_data(**kwargs)
        return context