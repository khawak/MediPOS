"""
MediPOS Payments — Views.

Provides views for recording customer/supplier payments and advances,
listing payment transactions, and managing dues.
"""
from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q, Subquery, OuterRef, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, ListView, TemplateView

from apps.customers.models import Customer
from apps.purchases.models import PurchaseOrder
from apps.sales.models import Sale
from apps.suppliers.models import Supplier

from .forms import PaymentForm
from .models import DueSettlement, PaymentTransaction


def get_payee(content_type_slug, object_id):
    """
    Resolve a payee from content_type_slug and object_id.

    Args:
        content_type_slug: 'customer' or 'supplier'.
        object_id: The primary key of the payee.

    Returns:
        tuple: (payee_instance, content_type_instance) or raises Http404.
    """
    model_map = {
        'customer': Customer,
        'supplier': Supplier,
    }
    model = model_map.get(content_type_slug)
    if not model:
        from django.http import Http404
        raise Http404(_('Invalid payee type.'))
    payee = get_object_or_404(model, pk=object_id)
    ct = ContentType.objects.get_for_model(payee)
    return payee, ct


class PaymentCreateView(LoginRequiredMixin, CreateView):
    """
    Record a payment or advance for a Customer or Supplier.

    URL pattern: /payments/add/<content_type_slug>/<object_id>/
    e.g., /payments/add/customer/5/  or  /payments/add/supplier/3/
    """

    model = PaymentTransaction
    form_class = PaymentForm
    template_name = 'payments/payment_form.html'

    def dispatch(self, request, *args, **kwargs):
        """Resolve the payee before dispatching."""
        self.payee, self.payee_ct = get_payee(
            kwargs.get('content_type_slug'),
            kwargs.get('object_id'),
        )
        self.payee_type = kwargs.get('content_type_slug')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass payee info to the form for filtering sale/PO queryset."""
        kwargs = super().get_form_kwargs()
        kwargs['payee_type'] = self.payee_type
        kwargs['payee'] = self.payee
        return kwargs

    def get_context_data(self, **kwargs):
        """Add payee info, outstanding dues, and recent transactions."""
        context = super().get_context_data(**kwargs)
        context['payee'] = self.payee
        context['payee_type'] = self.payee_type

        # Calculate outstanding dues for this payee
        if self.payee_type == 'customer':
            context['outstanding_dues'] = self._get_customer_outstanding()
        elif self.payee_type == 'supplier':
            context['outstanding_dues'] = self._get_supplier_outstanding()

        context['recent_transactions'] = PaymentTransaction.objects.filter(
            content_type=self.payee_ct,
            object_id=self.payee.pk,
        ).select_related('created_by', 'sale', 'purchase_order')[:10]
        return context

    def _get_customer_outstanding(self):
        """Calculate outstanding dues for a customer."""
        if self.payee.balance < 0:
            return abs(self.payee.balance)
        return Decimal('0.00')

    def _get_supplier_outstanding(self):
        """Calculate outstanding dues for a supplier."""
        if self.payee.balance < 0:
            return abs(self.payee.balance)
        return Decimal('0.00')

    def form_valid(self, form):
        """
        Set the payee and creator, then save.

        Also create DueSettlement records if invoice/PO is linked.
        The PaymentTransaction.save() method automatically updates
        the payee's balance.
        """
        form.instance.content_type = self.payee_ct
        form.instance.object_id = self.payee.pk
        form.instance.created_by = self.request.user

        # Manually assign the FK field from cleaned_data since it is
        # dynamically added in __init__ and not in Meta.fields.
        linked_sale = form.cleaned_data.get('sale')
        linked_po = form.cleaned_data.get('purchase_order')
        if linked_sale:
            form.instance.sale = linked_sale
        if linked_po:
            form.instance.purchase_order = linked_po

        response = super().form_valid(form)

        # Create DueSettlement if a sale or PO was linked
        tx = self.object
        if tx.sale_id and tx.amount:
            DueSettlement.objects.create(
                payment=tx,
                sale=tx.sale,
                amount_settled=tx.amount,
            )
        elif tx.purchase_order_id and tx.amount:
            DueSettlement.objects.create(
                payment=tx,
                purchase_order=tx.purchase_order,
                amount_settled=tx.amount,
            )

        # Refresh payee from DB to get the updated balance
        self.payee.refresh_from_db(fields=['balance'])

        payee_name = str(self.payee)
        messages.success(
            self.request,
            _('Payment of %(amount)s recorded for %(payee)s. '
              'New balance: %(balance)s')
            % {
                'amount': tx.amount,
                'payee': payee_name,
                'balance': self.payee.balance,
            },
        )
        return response

    def form_invalid(self, form):
        """Show validation errors to the user."""
        messages.error(
            self.request,
            _('Please correct the errors below and try again.'),
        )
        return super().form_invalid(form)

    def get_success_url(self):
        """Redirect back to the payee's detail page."""
        return self.payee.get_absolute_url()


class PaymentTransactionListView(LoginRequiredMixin, ListView):
    """
    List all payment transactions, filterable by payee type.

    Query params:
        type: 'customer' or 'supplier' to filter.
        q: search by payee name or reference.
    """

    model = PaymentTransaction
    template_name = 'payments/payment_list.html'
    context_object_name = 'transactions'
    paginate_by = 25

    def get_queryset(self):
        """Filter by type and/or search query."""
        queryset = PaymentTransaction.objects.select_related(
            'content_type', 'created_by', 'sale', 'purchase_order',
        ).all()

        payee_type = self.request.GET.get('type', '').strip()
        if payee_type == 'customer':
            ct = ContentType.objects.get_for_model(Customer)
            queryset = queryset.filter(content_type=ct)
        elif payee_type == 'supplier':
            ct = ContentType.objects.get_for_model(Supplier)
            queryset = queryset.filter(content_type=ct)

        search = self.request.GET.get('q', '').strip()
        if search:
            # Search by reference, note, OR payee name.
            # Since payee is a GenericForeignKey, we resolve matching
            # Customer/Supplier IDs and filter by (content_type, object_id).
            payee_q = Q()

            # Match customers by name
            customer_ct = ContentType.objects.get_for_model(Customer)
            matching_customer_ids = Customer.objects.filter(
                name__icontains=search,
            ).values_list('pk', flat=True)
            if matching_customer_ids:
                payee_q |= Q(
                    content_type=customer_ct,
                    object_id__in=matching_customer_ids,
                )

            # Match suppliers by name
            supplier_ct = ContentType.objects.get_for_model(Supplier)
            matching_supplier_ids = Supplier.objects.filter(
                name__icontains=search,
            ).values_list('pk', flat=True)
            if matching_supplier_ids:
                payee_q |= Q(
                    content_type=supplier_ct,
                    object_id__in=matching_supplier_ids,
                )

            queryset = queryset.filter(
                Q(reference__icontains=search)
                | Q(note__icontains=search)
                | payee_q
            )

        return queryset

    def get_context_data(self, **kwargs):
        """Add filter values and summary to context."""
        context = super().get_context_data(**kwargs)
        context['current_type'] = self.request.GET.get('type', '')
        context['search_query'] = self.request.GET.get('q', '')

        # Prefetch GenericForeignKey payees to avoid N+1 queries.
        # Group transactions by content_type, bulk-fetch payees,
        # and attach them via _cached_payee for use in payee_name.
        page_transactions = context.get('transactions')
        if page_transactions:
            ct_groups = {}
            for tx in page_transactions:
                ct_groups.setdefault(tx.content_type_id, []).append(tx)
            for ct_id, txs in ct_groups.items():
                ct = txs[0].content_type
                model_class = ct.model_class()
                if model_class:
                    obj_ids = [tx.object_id for tx in txs]
                    payees = model_class.objects.in_bulk(obj_ids)
                    for tx in txs:
                        tx._cached_payee = payees.get(tx.object_id)

        # Summary totals
        qs = self.get_queryset()
        context['total_received'] = qs.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        return context


# =============================================================================
# Due Management Views
# =============================================================================


class DueManagementDashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard overview of all dues - customer dues and supplier dues.

    Shows summary cards and quick-action buttons for managing outstanding
    payments.
    """

    template_name = 'payments/due_dashboard.html'

    def get_context_data(self, **kwargs):
        """Gather due statistics for customers and suppliers."""
        context = super().get_context_data(**kwargs)

        # -- Customer Dues --------------------------------------------------
        # Use per-invoice tracking (DueSettlement) instead of balance field
        customer_settled_subquery = Subquery(
            DueSettlement.objects.filter(
                sale__customer=OuterRef('pk'),
            ).values('sale__customer').annotate(
                total=models.Sum('amount_settled'),
            ).values('total'),
            output_field=models.DecimalField(),
        )

        customers_with_dues = Customer.objects.filter(
            is_active=True,
            sales__status='COMPLETED',
        ).annotate(
            total_dues_amount=(
                models.Sum('sales__grand_total')
                - Coalesce(models.Sum('sales__amount_paid'), Decimal('0.00'))
                - Coalesce(customer_settled_subquery, Decimal('0.00'))
            ),
        ).filter(
            total_dues_amount__gt=0,
        ).distinct().order_by('-total_dues_amount')

        context['customers_with_dues'] = customers_with_dues
        context['customer_dues_count'] = customers_with_dues.count()
        context['customer_dues_total'] = (
            customers_with_dues.aggregate(
                total=models.Sum('total_dues_amount')
            )['total'] or Decimal('0.00')
        )

        # Customers with advance (positive balance = they paid more than invoice totals)
        customers_with_advance = Customer.objects.filter(
            balance__gt=0,
            is_active=True,
        ).exclude(
            pk__in=customers_with_dues.values('pk'),
        ).order_by('-balance')
        context['customers_with_advance'] = customers_with_advance[:10]
        context['customer_advance_count'] = customers_with_advance.count()
        context['customer_advance_total'] = (
            customers_with_advance.aggregate(
                total=Sum('balance')
            )['total'] or Decimal('0.00')
        )

        # -- Supplier Dues --------------------------------------------------
        po_settled_subquery_dash = Subquery(
            DueSettlement.objects.filter(
                purchase_order__supplier=OuterRef('pk'),
            ).values('purchase_order__supplier').annotate(
                total=models.Sum('amount_settled'),
            ).values('total'),
            output_field=models.DecimalField(),
        )

        suppliers_with_dues = Supplier.objects.filter(
            is_active=True,
            purchase_orders__status='RECEIVED',
        ).annotate(
            total_dues_amount=(
                models.Sum('purchase_orders__total_amount')
                - Coalesce(po_settled_subquery_dash, Decimal('0.00'))
            ),
        ).filter(
            total_dues_amount__gt=0,
        ).distinct().order_by('-total_dues_amount')

        context['suppliers_with_dues'] = suppliers_with_dues
        context['supplier_dues_count'] = suppliers_with_dues.count()
        context['supplier_dues_total'] = (
            suppliers_with_dues.aggregate(
                total=models.Sum('total_dues_amount')
            )['total'] or Decimal('0.00')
        )

        suppliers_with_advance = Supplier.objects.filter(
            balance__gt=0,
            is_active=True,
        ).exclude(
            pk__in=suppliers_with_dues.values('pk'),
        ).order_by('-balance')
        context['suppliers_with_advance'] = suppliers_with_advance[:10]
        context['supplier_advance_count'] = suppliers_with_advance.count()
        context['supplier_advance_total'] = (
            suppliers_with_advance.aggregate(
                total=Sum('balance')
            )['total'] or Decimal('0.00')
        )

        # -- Recent payment activity ----------------------------------------
        context['recent_payments'] = PaymentTransaction.objects.select_related(
            'content_type', 'created_by',
        ).order_by('-created_at')[:15]

        # -- Sales with unpaid balances -------------------------------------
        # Annotate each sale with total settled via DueSettlement
        total_settled_subquery = Subquery(
            DueSettlement.objects.filter(
                sale=OuterRef('pk'),
            ).values('sale').annotate(
                total=models.Sum('amount_settled'),
            ).values('total'),
            output_field=models.DecimalField(),
        )
        context['unpaid_sales'] = Sale.objects.filter(
            status='COMPLETED',
            customer__isnull=False,
        ).select_related('customer').annotate(
            total_settled=Coalesce(total_settled_subquery, Decimal('0.00')),
            remaining=models.F('grand_total')
                       - models.F('amount_paid')
                       - Coalesce(total_settled_subquery, Decimal('0.00')),
        ).filter(
            grand_total__gt=models.F('amount_paid') + Coalesce(total_settled_subquery, Decimal('0.00')),
        ).order_by('-sale_date')[:20]

        # -- Unpaid POs -----------------------------------------------------
        # Annotate each PO with total settled via DueSettlement
        po_settled_subquery = Subquery(
            DueSettlement.objects.filter(
                purchase_order=OuterRef('pk'),
            ).values('purchase_order').annotate(
                total=models.Sum('amount_settled'),
            ).values('total'),
            output_field=models.DecimalField(),
        )
        context['received_pos'] = PurchaseOrder.objects.filter(
            status='RECEIVED',
            supplier__isnull=False,
        ).select_related('supplier').annotate(
            total_settled=Coalesce(po_settled_subquery, Decimal('0.00')),
            paid=Coalesce(po_settled_subquery, Decimal('0.00')),
            remaining=models.F('total_amount')
                       - Coalesce(po_settled_subquery, Decimal('0.00')),
        ).filter(
            total_amount__gt=Coalesce(po_settled_subquery, Decimal('0.00')),
        ).order_by('-order_date')[:20]

        return context


class CustomerDueListView(LoginRequiredMixin, ListView):
    """
    List all customers with outstanding dues (unpaid invoices).
    Uses per-invoice outstanding tracking via DueSettlement, not
    the running cash balance field.
    """

    model = Customer
    template_name = 'payments/customer_due_list.html'
    context_object_name = 'customers'
    paginate_by = 25

    def get_queryset(self):
        """
        Return customers who have at least one COMPLETED sale where
        grand_total is greater than amount_paid + total DueSettlement
        (i.e. there is still an outstanding amount on that invoice).
        Customers are annotated with their total outstanding amount.
        """
        total_settled_subquery = Subquery(
            DueSettlement.objects.filter(
                sale__customer=OuterRef('pk'),
            ).values('sale__customer').annotate(
                total=models.Sum('amount_settled'),
            ).values('total'),
            output_field=models.DecimalField(),
        )

        return Customer.objects.filter(
            is_active=True,
            sales__status='COMPLETED',
        ).annotate(
            total_dues_amount=(
                models.Sum('sales__grand_total')
                - Coalesce(models.Sum('sales__amount_paid'), Decimal('0.00'))
                - Coalesce(total_settled_subquery, Decimal('0.00'))
            ),
        ).filter(
            total_dues_amount__gt=0,
        ).distinct().order_by('-total_dues_amount')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['total_dues'] = (
            qs.aggregate(total=models.Sum('total_dues_amount'))['total']
            or Decimal('0.00')
        )
        return context


class SupplierDueListView(LoginRequiredMixin, ListView):
    """
    List all suppliers with outstanding dues (unpaid purchase orders).
    Uses per-PO outstanding tracking via DueSettlement, not the
    running cash balance field.
    """

    model = Supplier
    template_name = 'payments/supplier_due_list.html'
    context_object_name = 'suppliers'
    paginate_by = 25

    def get_queryset(self):
        """
        Return suppliers who have at least one RECEIVED purchase order
        where total_amount is greater than the total paid via DueSettlement
        (i.e. there is still an outstanding amount on that PO).
        Suppliers are annotated with their total outstanding amount.
        """
        po_settled_subquery = Subquery(
            DueSettlement.objects.filter(
                purchase_order__supplier=OuterRef('pk'),
            ).values('purchase_order__supplier').annotate(
                total=models.Sum('amount_settled'),
            ).values('total'),
            output_field=models.DecimalField(),
        )

        return Supplier.objects.filter(
            is_active=True,
            purchase_orders__status='RECEIVED',
        ).annotate(
            total_dues_amount=(
                models.Sum('purchase_orders__total_amount')
                - Coalesce(po_settled_subquery, Decimal('0.00'))
            ),
        ).filter(
            total_dues_amount__gt=0,
        ).distinct().order_by('-total_dues_amount')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['total_dues'] = (
            qs.aggregate(total=models.Sum('total_dues_amount'))['total']
            or Decimal('0.00')
        )
        return context


class DueSettleView(LoginRequiredMixin, TemplateView):
    """
    Settle dues for a specific customer or supplier with detailed breakdown.

    GET: Shows a form to record payment with breakdown of which
         invoices/POs are being settled.
    POST: Creates PaymentTransaction and DueSettlement records.
    """

    template_name = 'payments/due_settle.html'

    def dispatch(self, request, *args, **kwargs):
        """Resolve the payee."""
        self.payee_type = kwargs.get('content_type_slug')
        self.payee, self.payee_ct = get_payee(
            self.payee_type,
            kwargs.get('object_id'),
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Provide payee details and outstanding breakdown."""
        context = super().get_context_data(**kwargs)
        context['payee'] = self.payee
        context['payee_type'] = self.payee_type

        if self.payee_type == 'customer':
            context['outstanding_items'] = self._get_customer_outstanding_items()
            context['total_outstanding'] = sum(
                item['remaining'] for item in context['outstanding_items']
            )
        else:
            context['outstanding_items'] = self._get_supplier_outstanding_items()
            context['total_outstanding'] = sum(
                item['remaining'] for item in context['outstanding_items']
            )

        context['recent_transactions'] = PaymentTransaction.objects.filter(
            content_type=self.payee_ct,
            object_id=self.payee.pk,
        ).select_related('created_by', 'sale', 'purchase_order').order_by('-created_at')[:15]

        return context

    def _get_customer_outstanding_items(self):
        """Get all unpaid/partially-paid sales invoices for this customer."""
        sales = Sale.objects.filter(
            customer=self.payee,
            status='COMPLETED',
        ).order_by('-sale_date')

        items = []
        for sale in sales:
            total_settled = DueSettlement.objects.filter(
                sale=sale,
            ).aggregate(total=Sum('amount_settled'))['total'] or Decimal('0.00')
            remaining = sale.grand_total - sale.amount_paid - total_settled
            if remaining > 0:
                items.append({
                    'type': 'invoice',
                    'ref': sale.invoice_no,
                    'date': sale.sale_date,
                    'total': sale.grand_total,
                    'paid': sale.amount_paid + total_settled,
                    'remaining': remaining,
                    'sale_id': sale.pk,
                })
        return items

    def _get_supplier_outstanding_items(self):
        """Get all received POs for this supplier."""
        pos = PurchaseOrder.objects.filter(
            supplier=self.payee,
            status='RECEIVED',
        ).order_by('-order_date')

        items = []
        for po in pos:
            total_paid = DueSettlement.objects.filter(
                purchase_order=po,
            ).aggregate(total=Sum('amount_settled'))['total'] or Decimal('0.00')
            remaining = po.total_amount - total_paid
            if remaining > 0:
                items.append({
                    'type': 'po',
                    'ref': po.po_number,
                    'date': po.order_date,
                    'total': po.total_amount,
                    'paid': total_paid,
                    'remaining': remaining,
                    'po_id': po.pk,
                })
        return items

    def post(self, request, *args, **kwargs):
        """Process a due settlement payment."""
        amount = request.POST.get('amount', '0')
        payment_method = request.POST.get('payment_method', 'CASH')
        reference = request.POST.get('reference', '')
        note = request.POST.get('note', '')
        transaction_date_str = request.POST.get('transaction_date', '')

        # Validate payment_method against allowed choices
        valid_methods = [choice[0] for choice in PaymentTransaction.PAYMENT_METHODS]
        if payment_method not in valid_methods:
            messages.error(
                request,
                _('Invalid payment method. Please select a valid option.'),
            )
            return self.render_to_response(self.get_context_data())

        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError('Amount must be positive.')
        except (ValueError, TypeError):
            messages.error(request, _('Please enter a valid positive amount.'))
            return self.render_to_response(self.get_context_data())

        # Parse transaction date
        try:
            transaction_date = datetime.strptime(
                transaction_date_str, '%Y-%m-%d'
            ).date() if transaction_date_str else date.today()
        except (ValueError, TypeError):
            transaction_date = date.today()

        # Create the payment transaction
        tx = PaymentTransaction.objects.create(
            content_type=self.payee_ct,
            object_id=self.payee.pk,
            amount=amount,
            transaction_type='PAYMENT',
            payment_method=payment_method,
            reference=reference,
            note=note,
            transaction_date=transaction_date,
            created_by=request.user,
        )

        # Process individual settlement allocations from POST data
        allocation_keys = [k for k in request.POST.keys() if k.startswith('settle_')]
        total_allocated = Decimal('0.00')

        for key in allocation_keys:
            allocated_str = request.POST.get(key, '0')
            try:
                allocated = Decimal(allocated_str)
                if allocated <= 0:
                    continue
            except (ValueError, TypeError):
                continue

            total_allocated += allocated

            if key.startswith('settle_invoice_'):
                sale_id = key.replace('settle_invoice_', '')
                sale = Sale.objects.filter(pk=sale_id).first()
                if sale:
                    DueSettlement.objects.create(
                        payment=tx,
                        sale=sale,
                        amount_settled=allocated,
                    )
            elif key.startswith('settle_po_'):
                po_id = key.replace('settle_po_', '')
                po = PurchaseOrder.objects.filter(pk=po_id).first()
                if po:
                    DueSettlement.objects.create(
                        payment=tx,
                        purchase_order=po,
                        amount_settled=allocated,
                    )

        # Detect manual allocations — if none were specified, auto-distribute
        # the payment amount across outstanding items (oldest first / FIFO).
        has_manual_allocations = total_allocated > 0

        if not has_manual_allocations and amount > 0:
            remaining_to_allocate = amount
            if self.payee_type == 'customer':
                items = self._get_customer_outstanding_items()
            else:
                items = self._get_supplier_outstanding_items()

            for item in items:
                if remaining_to_allocate <= 0:
                    break
                alloc = min(item['remaining'], remaining_to_allocate)
                remaining_to_allocate -= alloc

                if self.payee_type == 'customer':
                    sale = Sale.objects.filter(pk=item['sale_id']).first()
                    if sale:
                        DueSettlement.objects.create(
                            payment=tx,
                            sale=sale,
                            amount_settled=alloc,
                        )
                else:
                    po = PurchaseOrder.objects.filter(pk=item['po_id']).first()
                    if po:
                        DueSettlement.objects.create(
                            payment=tx,
                            purchase_order=po,
                            amount_settled=alloc,
                        )
            total_allocated = amount - remaining_to_allocate

        # Validate that allocation total does not exceed payment amount
        if total_allocated > amount:
            messages.warning(
                request,
                _('Allocation total (৳%(allocated)s) exceeds payment amount '
                  '(৳%(amount)s). Unallocated overage has been discarded.')
                % {'allocated': total_allocated, 'amount': amount},
            )

        # Refresh balance
        self.payee.refresh_from_db(fields=['balance'])

        messages.success(
            request,
            _('Due payment of %(amount)s recorded for %(payee)s. '
              'New balance: %(balance)s')
            % {
                'amount': amount,
                'payee': str(self.payee),
                'balance': self.payee.balance,
            },
        )

        # Redirect to the appropriate dues list after settlement
        if self.payee_type == 'customer':
            return redirect(reverse_lazy('payments:customer_dues'))
        else:
            return redirect(reverse_lazy('payments:supplier_dues'))