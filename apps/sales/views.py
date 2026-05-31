"""
MediPOS Sales — Views.

Class-based and function-based views for the point-of-sale billing
interface, cart management (session-based), checkout, invoice display,
and sale history. All views require authentication.
"""
import json
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView, TemplateView

from apps.customers.models import Customer
from django.contrib.contenttypes.models import ContentType
from apps.inventory.models import Batch, StockLedger
from apps.medicines.models import Category, Medicine

from .models import Sale, SaleItem, generate_invoice_number


# ═══════════════════════════════════════════════════════════════════════════════
# Session Cart Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def get_cart(request):
    """
    Retrieve the POS cart from the session.

    The cart is a dict mapping str(medicine_id) to a dict with keys:
        id, name, price, tax_rate, quantity, discount.

    Args:
        request: The HTTP request object.

    Returns:
        dict: The cart data, or an empty dict if no cart exists.
    """
    return request.session.get('pos_cart', {})


def save_cart(request, cart):
    """
    Save the POS cart to the session.

    Args:
        request: The HTTP request object.
        cart: The cart dict to persist.
    """
    request.session['pos_cart'] = cart
    request.session.modified = True


def clear_cart(request):
    """Remove the POS cart from the session."""
    request.session.pop('pos_cart', None)
    request.session.pop('pos_customer', None)
    request.session.pop('pos_discount', None)
    request.session.modified = True


def calculate_cart_totals(cart):
    """
    Calculate subtotal, discount, tax, and grand total from cart data.

    Args:
        cart: The session cart dict {med_id: {price, quantity, discount, tax_rate}}.

    Returns:
        dict: Keys: subtotal, discount, tax, grand_total — all as Decimal.
    """
    subtotal = Decimal('0.00')
    total_tax = Decimal('0.00')
    total_item_discount = Decimal('0.00')

    for item in cart.values():
        price = Decimal(str(item.get('price', 0)))
        qty = int(item.get('quantity', 1))
        item_discount = Decimal(str(item.get('discount', 0)))
        tax_rate = Decimal(str(item.get('tax_rate', 15)))

        line_before_tax = price * qty - item_discount
        tax_amount = line_before_tax * tax_rate / Decimal('100')

        subtotal += line_before_tax
        total_tax += tax_amount
        total_item_discount += item_discount

    grand_total = subtotal + total_tax

    return {
        'subtotal': subtotal,
        'discount': total_item_discount,
        'tax': total_tax,
        'grand_total': grand_total,
    }


def cart_to_json(cart):
    """
    Convert the cart dict to a JSON-safe structure including totals.

    Args:
        cart: The session cart dict.

    Returns:
        dict: Cart data with items list and computed totals.
    """
    items = []
    for med_id, data in cart.items():
        items.append({
            'id': data.get('id'),
            'name': data.get('name'),
            'price': str(data.get('price', 0)),
            'tax_rate': str(data.get('tax_rate', 15)),
            'quantity': int(data.get('quantity', 1)),
            'discount': str(data.get('discount', 0)),
        })

    totals = calculate_cart_totals(cart)

    return {
        'items': items,
        'count': len(items),
        'subtotal': str(totals['subtotal']),
        'discount': str(totals['discount']),
        'tax': str(totals['tax']),
        'grand_total': str(totals['grand_total']),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# POS Main View
# ═══════════════════════════════════════════════════════════════════════════════


class POSView(LoginRequiredMixin, TemplateView):
    """
    The main Point-of-Sale billing screen.

    Displays a split-panel interface: left panel for medicine search
    and product grid, right panel for cart management and checkout.
    All cart operations are handled via AJAX to the cart API endpoints.
    """

    template_name = 'sales/pos.html'

    def get_context_data(self, **kwargs):
        """
        Add active medicines, categories, and recent customers to context.
        """
        context = super().get_context_data(**kwargs)
        context['medicines'] = Medicine.objects.filter(
            is_active=True,
            stock_quantity__gt=0,
        ).select_related('category').order_by('name')
        context['categories'] = Category.objects.filter(
            is_active=True,
            medicines__isnull=False,
        ).distinct().order_by('name')
        context['recent_customers'] = Customer.objects.filter(
            is_active=True,
        ).order_by('-created_at')[:50]
        context['held_sales'] = Sale.objects.filter(
            status=Sale.Status.HELD,
        ).order_by('-created_at')[:20]
        return context


# ═══════════════════════════════════════════════════════════════════════════════
# Cart API Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


class CartGetView(LoginRequiredMixin, View):
    """
    Return the current cart state as JSON.

    GET only — used for initial page load and cart refresh.
    """

    def get(self, request):
        """Serialize and return the current session cart."""
        cart = get_cart(request)
        return JsonResponse({'success': True, 'cart': cart_to_json(cart)})


class CartAddItemView(LoginRequiredMixin, View):
    """
    Add a medicine to the session cart via POST.

    Expects JSON body: {'medicine_id': int, 'quantity': int (optional)}.
    If the medicine is already in the cart, increments the quantity.
    """

    def post(self, request):
        """Add or increment a medicine in the cart."""
        try:
            data = json.loads(request.body)
            medicine_id = int(data.get('medicine_id', 0))
            quantity = int(data.get('quantity', 1))
        except (json.JSONDecodeError, ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid request data.'}, status=400)

        medicine = get_object_or_404(Medicine, pk=medicine_id, is_active=True)

        cart = get_cart(request)
        med_key = str(medicine_id)

        if med_key in cart:
            cart[med_key]['quantity'] += quantity
        else:
            cart[med_key] = {
                'id': medicine.pk,
                'name': str(medicine),
                'price': str(medicine.selling_price),
                'tax_rate': str(medicine.tax_rate),
                'quantity': quantity,
                'discount': '0.00',
            }

        save_cart(request, cart)
        return JsonResponse({
            'success': True,
            'message': f'{medicine.name} added to cart.',
            'cart': cart_to_json(cart),
        })


class CartRemoveItemView(LoginRequiredMixin, View):
    """
    Remove a medicine from the session cart via POST.

    Expects JSON body: {'medicine_id': int}.
    """

    def post(self, request):
        """Remove an item from the cart by medicine ID."""
        try:
            data = json.loads(request.body)
            medicine_id = int(data.get('medicine_id', 0))
        except (json.JSONDecodeError, ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid request data.'}, status=400)

        cart = get_cart(request)
        med_key = str(medicine_id)

        if med_key in cart:
            removed_name = cart[med_key].get('name', 'Item')
            del cart[med_key]
            save_cart(request, cart)
            return JsonResponse({
                'success': True,
                'message': f'{removed_name} removed from cart.',
                'cart': cart_to_json(cart),
            })

        return JsonResponse({'success': False, 'error': 'Item not in cart.'}, status=404)


class CartUpdateQuantityView(LoginRequiredMixin, View):
    """
    Update the quantity of a cart item via POST.

    Expects JSON body: {'medicine_id': int, 'quantity': int}.
    If quantity is 0 or less, the item is removed.
    """

    def post(self, request):
        """Update quantity and/or discount for a cart item."""
        try:
            data = json.loads(request.body)
            medicine_id = int(data.get('medicine_id', 0))
            quantity = data.get('quantity')
            discount = data.get('discount')
        except (json.JSONDecodeError, ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid request data.'}, status=400)

        cart = get_cart(request)
        med_key = str(medicine_id)

        if med_key not in cart:
            return JsonResponse({'success': False, 'error': 'Item not in cart.'}, status=404)

        if quantity is not None:
            quantity = int(quantity)
            if quantity <= 0:
                del cart[med_key]
                save_cart(request, cart)
                return JsonResponse({
                    'success': True,
                    'message': 'Item removed from cart.',
                    'cart': cart_to_json(cart),
                })
            cart[med_key]['quantity'] = quantity

        if discount is not None:
            cart[med_key]['discount'] = str(discount)

        save_cart(request, cart)
        return JsonResponse({
            'success': True,
            'cart': cart_to_json(cart),
        })


class CartUpdateDiscountView(LoginRequiredMixin, View):
    """
    Update the cart-level discount via POST.

    Expects JSON body: {'discount_type': 'percent'|'flat', 'discount_value': float}.
    Stores discount info in session; totals are recalculated on checkout.
    """

    def post(self, request):
        """Set cart-level discount type and value."""
        try:
            data = json.loads(request.body)
            discount_type = data.get('discount_type', 'flat')
            discount_value = data.get('discount_value', 0)
        except (json.JSONDecodeError, ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid request data.'}, status=400)

        request.session['pos_discount'] = {
            'type': discount_type,
            'value': str(discount_value),
        }
        request.session.modified = True

        cart = get_cart(request)
        totals = calculate_cart_totals(cart)

        # Apply cart-level discount
        subtotal = totals['subtotal']
        tax = totals['tax']

        if discount_type == 'percent':
            discount_amount = subtotal * Decimal(str(discount_value)) / Decimal('100')
        else:
            discount_amount = Decimal(str(discount_value))

        grand_total = subtotal + tax - discount_amount

        return JsonResponse({
            'success': True,
            'subtotal': str(subtotal),
            'discount_amount': str(discount_amount),
            'tax': str(tax),
            'grand_total': str(max(grand_total, Decimal('0.00'))),
        })


class CartSetCustomerView(LoginRequiredMixin, View):
    """
    Set the customer for the current sale via POST.

    Expects JSON body: {'customer_id': int or null}.
    Stores the customer ID in the session.
    """

    def post(self, request):
        """Set the customer for the cart session."""
        try:
            data = json.loads(request.body)
            customer_id = data.get('customer_id')
        except (json.JSONDecodeError, ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid request data.'}, status=400)

        if customer_id:
            customer = get_object_or_404(Customer, pk=customer_id, is_active=True)
            request.session['pos_customer'] = customer.pk
            request.session.modified = True
            return JsonResponse({
                'success': True,
                'customer': {'id': customer.pk, 'name': customer.name, 'phone': customer.phone},
            })
        else:
            request.session.pop('pos_customer', None)
            request.session.modified = True
            return JsonResponse({'success': True, 'customer': None})


class MedicineSearchView(LoginRequiredMixin, View):
    """
    Search medicines for the POS product grid via GET.

    Query param 'q' searches across name, generic_name, brand, and barcode.
    Returns a JSON list of matching active medicines with stock details.
    """

    def get(self, request):
        """Search and return matching medicines as JSON."""
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'success': True, 'medicines': []})

        medicines = Medicine.objects.filter(is_active=True).filter(
            Q(name__icontains=query)
            | Q(generic_name__icontains=query)
            | Q(brand__icontains=query)
            | Q(barcode__icontains=query)
        ).select_related('category')[:30]

        results = []
        for med in medicines:
            results.append({
                'id': med.pk,
                'name': med.name,
                'generic_name': med.generic_name,
                'brand': med.brand,
                'barcode': med.barcode or '',
                'selling_price': str(med.selling_price),
                'stock_quantity': med.stock_quantity,
                'tax_rate': str(med.tax_rate),
                'category': med.category.name if med.category else '',
                'unit': med.unit,
            })

        return JsonResponse({'success': True, 'medicines': results})


# ═══════════════════════════════════════════════════════════════════════════════
# Checkout View
# ═══════════════════════════════════════════════════════════════════════════════


class CheckoutView(LoginRequiredMixin, View):
    """
    Process the session cart into a completed Sale transaction.

    POST only. Validates the cart is not empty, creates a Sale record
    with auto-generated invoice number, creates SaleItem entries, and
    records StockLedger OUT entries that trigger Medicine.stock_quantity
    updates via the existing inventory signal.
    """

    def post(self, request):
        """Process the cart and create a completed sale."""
        cart = get_cart(request)
        if not cart:
            messages.error(request, _('Cart is empty. Add items before checkout.'))
            return redirect('sales:pos')

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, TypeError):
            # Fallback: the POS frontend submits via a hidden form field named 'body'
            body_param = request.POST.get('body', '')
            try:
                data = json.loads(body_param)
            except (json.JSONDecodeError, TypeError):
                data = {}

        payment_mode = data.get('payment_mode', 'CASH')
        amount_paid = Decimal(str(data.get('amount_paid', 0)))
        deferred = data.get('deferred', False)
        notes = data.get('notes', '')

        # Retrieve session-stored customer and discount
        customer_id = request.session.get('pos_customer')
        customer = None
        if customer_id:
            customer = Customer.objects.filter(pk=customer_id).first()

        # Deferred payment requires a customer
        if deferred and not customer:
            messages.error(request, _('Deferred payment requires a customer. Please select a customer first.'))
            return redirect('sales:pos')

        discount_info = request.session.get('pos_discount', {})

        totals = calculate_cart_totals(cart)
        subtotal = totals['subtotal']
        total_tax = totals['tax']

        # Apply cart-level discount
        discount_type = discount_info.get('type', 'flat')
        discount_value = Decimal(str(discount_info.get('value', 0)))

        if discount_type == 'percent':
            discount_amount = subtotal * discount_value / Decimal('100')
            discount_percent = discount_value
        else:
            discount_amount = discount_value
            discount_percent = Decimal('0.00')

        grand_total = subtotal + total_tax - discount_amount
        grand_total = max(grand_total, Decimal('0.00'))
        change_amount = max(amount_paid - grand_total, Decimal('0.00'))

        # For deferred payment, record the remaining as customer dues
        remaining = Decimal('0.00')
        if deferred and customer:
            remaining = grand_total - amount_paid
            # PaymentTransaction.save() automatically updates customer.balance
            # by adding the amount. A negative amount = customer now owes (dues).
            from apps.payments.models import PaymentTransaction

        with transaction.atomic():
            # Create the Sale
            invoice_no = generate_invoice_number()
            sale = Sale.objects.create(
                invoice_no=invoice_no,
                customer=customer,
                cashier=request.user,
                subtotal=subtotal,
                discount_amount=discount_amount,
                discount_percent=discount_percent,
                tax_amount=total_tax,
                grand_total=grand_total,
                payment_mode=payment_mode,
                amount_paid=amount_paid,
                change_amount=change_amount,
                status=Sale.Status.COMPLETED,
                notes=notes,
            )

            # Create deferred payment transaction if applicable
            if deferred and customer and remaining > 0:
                PaymentTransaction.objects.create(
                    content_type=ContentType.objects.get_for_model(customer),
                    object_id=customer.pk,
                    amount=-remaining,
                    transaction_type='PAYMENT',
                    payment_method='CASH',
                    reference=f'Deferred: Sale',
                    note=f'Auto-created dues from deferred payment on invoice {invoice_no}',
                    created_by=request.user,
                )

            # Create SaleItems and StockLedger OUT entries
            for med_key, item in cart.items():
                medicine = Medicine.objects.filter(pk=int(med_key)).first()
                if not medicine:
                    continue

                qty = int(item.get('quantity', 1))
                unit_price = Decimal(str(item.get('price', 0)))
                item_discount = Decimal(str(item.get('discount', 0)))
                tax_rate = Decimal(str(item.get('tax_rate', 15)))

                line_before_tax = unit_price * qty - item_discount
                tax_amount = line_before_tax * tax_rate / Decimal('100')
                line_total = line_before_tax + tax_amount

                # Find the best batch (FEFO — First Expiry First Out)
                batch = (
                    Batch.objects.filter(
                        medicine=medicine,
                        is_active=True,
                        expiry_date__gte=date.today(),
                        quantity__gte=qty,
                    )
                    .order_by('expiry_date')
                    .first()
                )

                # Create SaleItem
                SaleItem.objects.create(
                    sale=sale,
                    medicine=medicine,
                    batch=batch,
                    quantity=qty,
                    unit_price=unit_price,
                    discount=item_discount,
                    tax_rate=tax_rate,
                    line_total=line_total,
                )

                # Deduct from batch quantity if a batch was selected
                if batch:
                    batch.quantity -= qty
                    batch.save(update_fields=['quantity'])

                # Create StockLedger OUT entry → triggers signal to update Medicine.stock_quantity
                StockLedger.objects.create(
                    medicine=medicine,
                    batch=batch,
                    transaction_type='OUT',
                    quantity=-qty,
                    reference=sale.invoice_no,
                    note=f'Sale: {sale.invoice_no}',
                    created_by=request.user,
                )

        # Clear the cart after successful checkout
        clear_cart(request)

        if deferred and customer and remaining > 0:
            messages.success(
                request,
                _('Sale completed (deferred)! Invoice #%(invoice)s — Paid: ৳%(paid)s — Dues: ৳%(dues)s') % {
                    'invoice': sale.invoice_no,
                    'paid': f'{amount_paid:,.2f}',
                    'dues': f'{remaining:,.2f}',
                },
            )
        else:
            messages.success(
                request,
                _('Sale completed! Invoice #%(invoice)s — Total: ৳%(total)s') % {
                    'invoice': sale.invoice_no,
                    'total': f'{grand_total:,.2f}',
                },
            )
        return redirect('sales:invoice_detail', pk=sale.pk)


# ═══════════════════════════════════════════════════════════════════════════════
# Invoice / Receipt Views
# ═══════════════════════════════════════════════════════════════════════════════


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    """
    Display a full A4-style invoice/receipt for a completed sale.

    Shows the shop info header, customer details, itemized table,
    and payment summary.
    """

    model = Sale
    template_name = 'sales/invoice_detail.html'
    context_object_name = 'sale'

    def get_queryset(self):
        """Prefetch related items and medicines for efficient rendering."""
        return Sale.objects.select_related('customer', 'cashier').prefetch_related(
            'items__medicine',
        )


class InvoicePrintView(LoginRequiredMixin, DetailView):
    """
    Display a minimal A4 print-optimized invoice.

    Uses a dedicated print-friendly template that auto-triggers
    the browser print dialog on load.
    """

    model = Sale
    template_name = 'sales/invoice_print.html'
    context_object_name = 'sale'

    def get_queryset(self):
        """Prefetch related items and medicines."""
        return Sale.objects.select_related('customer', 'cashier').prefetch_related(
            'items__medicine',
        )


class InvoiceThermalPrintView(LoginRequiredMixin, DetailView):
    """
    Display an ultra-compact 80mm thermal receipt style invoice.

    Uses a minimal template designed for thermal/pos printers with
    small font and compact layout.
    """

    model = Sale
    template_name = 'sales/invoice_thermal.html'
    context_object_name = 'sale'

    def get_queryset(self):
        """Prefetch related items and medicines."""
        return Sale.objects.select_related('customer', 'cashier').prefetch_related(
            'items__medicine',
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Sale History Views
# ═══════════════════════════════════════════════════════════════════════════════


class SaleListView(LoginRequiredMixin, ListView):
    """
    Display a paginated, filterable list of all sales.

    Supports filtering by date range, payment mode, status, and
    search by invoice number.
    """

    model = Sale
    template_name = 'sales/sale_list.html'
    context_object_name = 'sales'
    paginate_by = 25
    ordering = ['-sale_date']

    def get_queryset(self):
        """
        Apply optional filters from GET parameters.

        Supports:
            - q: search by invoice_no
            - date_from / date_to: filter by sale date range
            - status: filter by sale status
            - payment_mode: filter by payment method
        """
        queryset = Sale.objects.select_related('customer', 'cashier').prefetch_related('items')

        # Search
        search = self.request.GET.get('q', '').strip()
        if search:
            queryset = queryset.filter(invoice_no__icontains=search)

        # Date range
        date_from = self.request.GET.get('date_from', '').strip()
        date_to = self.request.GET.get('date_to', '').strip()
        if date_from:
            queryset = queryset.filter(sale_date__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(sale_date__date__lte=date_to)

        # Status filter
        status = self.request.GET.get('status', '').strip()
        if status:
            queryset = queryset.filter(status=status)

        # Payment mode filter
        payment_mode = self.request.GET.get('payment_mode', '').strip()
        if payment_mode:
            queryset = queryset.filter(payment_mode=payment_mode)

        return queryset

    def get_context_data(self, **kwargs):
        """Add filter values, status/payment choices, and summary totals to context."""
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Sale.Status.choices
        context['payment_mode_choices'] = Sale.PaymentMode.choices
        context['current_filters'] = {
            'q': self.request.GET.get('q', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'status': self.request.GET.get('status', ''),
            'payment_mode': self.request.GET.get('payment_mode', ''),
        }

        # Calculate summary totals for the filtered queryset (all pages)
        filtered_qs = self.get_queryset().filter(status='COMPLETED')
        totals = filtered_qs.aggregate(
            total_revenue=Sum('grand_total'),
            sale_count=Count('pk'),
        )
        context['total_revenue'] = totals['total_revenue'] or 0
        context['completed_count'] = totals['sale_count'] or 0
        if context['completed_count'] > 0:
            context['avg_revenue'] = context['total_revenue'] / context['completed_count']
        else:
            context['avg_revenue'] = 0

        # Total dues: sum of (grand_total - amount_paid) for unpaid sales
        from decimal import Decimal
        dues_qs = filtered_qs.filter(grand_total__gt=F('amount_paid'))
        total_dues = dues_qs.aggregate(
            total=Sum(F('grand_total') - F('amount_paid'))
        )['total'] or Decimal('0.00')
        context['total_dues'] = total_dues

        # Total items sold across all filtered sales
        total_items_sold = SaleItem.objects.filter(sale__in=filtered_qs).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        context['total_items_sold'] = total_items_sold

        return context


class SaleDetailView(LoginRequiredMixin, DetailView):
    """
    Display full details of a single sale.

    Shows the invoice info card, customer details, item table,
    financial summary, and action buttons (print, cancel).
    """

    model = Sale
    template_name = 'sales/sale_detail.html'
    context_object_name = 'sale'

    def get_queryset(self):
        """Prefetch related items and medicines."""
        return Sale.objects.select_related('customer', 'cashier').prefetch_related(
            'items__medicine', 'items__batch',
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Hold / Resume / Cancel Views
# ═══════════════════════════════════════════════════════════════════════════════


class HoldSaleView(LoginRequiredMixin, View):
    """
    Save the current session cart as a HELD sale.

    POST only. Creates a Sale with status='HELD' from the cart contents,
    then clears the session cart so the cashier can start a new transaction.
    """

    def post(self, request):
        """Hold the current cart as a sale draft."""
        cart = get_cart(request)
        if not cart:
            messages.error(request, _('Cart is empty. Nothing to hold.'))
            return redirect('sales:pos')

        totals = calculate_cart_totals(cart)
        customer_id = request.session.get('pos_customer')
        customer = None
        if customer_id:
            customer = Customer.objects.filter(pk=customer_id).first()

        sale = Sale.objects.create(
            invoice_no=generate_invoice_number(),
            customer=customer,
            cashier=request.user,
            subtotal=totals['subtotal'],
            discount_amount=Decimal('0.00'),
            discount_percent=Decimal('0.00'),
            tax_amount=totals['tax'],
            grand_total=totals['grand_total'],
            status=Sale.Status.HELD,
        )

        for med_key, item in cart.items():
            medicine = Medicine.objects.filter(pk=int(med_key)).first()
            if not medicine:
                continue

            qty = int(item.get('quantity', 1))
            unit_price = Decimal(str(item.get('price', 0)))
            item_discount = Decimal(str(item.get('discount', 0)))
            tax_rate = Decimal(str(item.get('tax_rate', 15)))

            line_before_tax = unit_price * qty - item_discount
            tax_amount = line_before_tax * tax_rate / Decimal('100')
            line_total = line_before_tax + tax_amount

            SaleItem.objects.create(
                sale=sale,
                medicine=medicine,
                quantity=qty,
                unit_price=unit_price,
                discount=item_discount,
                tax_rate=tax_rate,
                line_total=line_total,
            )

        clear_cart(request)
        messages.success(
            request,
            _('Sale held as draft — Invoice #%(invoice)s.') % {'invoice': sale.invoice_no},
        )
        return redirect('sales:pos')


class ResumeSaleView(LoginRequiredMixin, View):
    """
    Load a HELD sale back into the session cart.

    GET only. Takes a sale_id, loads its items into the session cart,
    deletes the held sale record, and redirects to the POS screen.
    """

    def get(self, request, sale_id):
        """Resume a held sale by loading it into the cart."""
        sale = get_object_or_404(Sale, pk=sale_id, status=Sale.Status.HELD)

        cart = {}
        for item in sale.items.all():
            med_key = str(item.medicine.pk)
            cart[med_key] = {
                'id': item.medicine.pk,
                'name': str(item.medicine),
                'price': str(item.unit_price),
                'tax_rate': str(item.tax_rate),
                'quantity': item.quantity,
                'discount': str(item.discount),
            }

        save_cart(request, cart)

        # Restore customer if present
        if sale.customer:
            request.session['pos_customer'] = sale.customer.pk

        # Delete the held sale (items cascade)
        sale.delete()

        messages.success(request, _('Held sale loaded into cart. Ready to checkout.'))
        return redirect('sales:pos')


class CancelSaleView(LoginRequiredMixin, View):
    """
    Cancel a completed sale and reverse stock movements.

    POST only. Sets the sale status to CANCELLED and creates StockLedger
    IN entries to restock the medicines sold in this transaction.
    """

    def post(self, request, pk):
        """Cancel a sale and restock inventory."""
        sale = get_object_or_404(Sale, pk=pk)

        if sale.status == Sale.Status.CANCELLED:
            messages.warning(request, _('This sale is already cancelled.'))
            return redirect('sales:sale_detail', pk=sale.pk)

        if sale.status == Sale.Status.REFUNDED:
            messages.warning(request, _('This sale has been refunded. Cannot cancel.'))
            return redirect('sales:sale_detail', pk=sale.pk)

        with transaction.atomic():
            sale.status = Sale.Status.CANCELLED
            sale.save(update_fields=['status', 'updated_at'])

            # Reverse stock: create IN entries for each item
            for item in sale.items.all():
                # Restore batch quantity
                if item.batch:
                    item.batch.quantity += item.quantity
                    item.batch.save(update_fields=['quantity'])

                StockLedger.objects.create(
                    medicine=item.medicine,
                    batch=item.batch,
                    transaction_type='IN',
                    quantity=item.quantity,
                    reference=f'Cancel: {sale.invoice_no}',
                    note=f'Cancellation restock for invoice {sale.invoice_no}',
                    created_by=request.user,
                )

        messages.success(
            request,
            _('Sale #%(invoice)s has been cancelled and stock restored.') % {
                'invoice': sale.invoice_no,
            },
        )
        return redirect('sales:sale_detail', pk=sale.pk)