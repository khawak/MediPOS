"""
MediPOS Customers — Views.

Class-based views for Customer management. All authenticated users
(Admin, Pharmacist, Cashier) can manage customers — cashiers need to
create walk-in customers at POS.
"""
import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import CustomerForm
from .models import Customer


# ═══════════════════════════════════════════════════════════════════════════════
# Customer Views
# ═══════════════════════════════════════════════════════════════════════════════


class CustomerListView(LoginRequiredMixin, ListView):
    """
    Display a paginated, searchable list of all customers.

    Supports search by name, phone, or email via GET parameter 'q'.
    """

    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 25
    ordering = ['name']

    def get_queryset(self):
        """Optionally filter by search query across name, phone, and email."""
        queryset = Customer.objects.all()
        search = self.request.GET.get('q', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        """Add the search query string to template context."""
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q', '').strip()
        return context


class CustomerDetailView(LoginRequiredMixin, DetailView):
    """
    Display the full details of a single customer.

    Shows all fields, loyalty points, balance, status badge, and
    payment transaction history.
    """

    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'

    def get_object(self, queryset=None):
        """Fetch the customer or return a 404."""
        return get_object_or_404(Customer, pk=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        """Add recent payment transactions to the context."""
        context = super().get_context_data(**kwargs)
        from apps.payments.models import PaymentTransaction
        from django.contrib.contenttypes.models import ContentType
        customer_ct = ContentType.objects.get_for_model(Customer)
        context['transactions'] = PaymentTransaction.objects.filter(
            content_type=customer_ct,
            object_id=self.object.pk,
        ).select_related('created_by').order_by('-created_at')[:10]
        return context


class CustomerCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new customer record.

    Displays a success message and redirects to the customer detail view.
    """

    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'

    def form_valid(self, form):
        """Add a success message after creating the customer."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            _('Customer "%s" created successfully.') % self.object.name,
        )
        return response


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an existing customer record.

    Displays a success message and redirects to the customer detail view.
    """

    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'

    def form_valid(self, form):
        """Add a success message after updating the customer."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            _('Customer "%s" updated successfully.') % self.object.name,
        )
        return response


class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    """
    Permanently delete a customer from the database.

    Confirms with the user before deleting. Redirects to the customer list.
    """

    model = Customer
    template_name = 'customers/customer_confirm_delete.html'
    success_url = reverse_lazy('customers:customer_list')

    def get_object(self, queryset=None):
        """Fetch the customer or return a 404."""
        return get_object_or_404(Customer, pk=self.kwargs.get('pk'))

    def form_valid(self, form):
        """Hard-delete: permanently remove the customer record."""
        messages.success(
            self.request,
            _('Customer "%s" deleted successfully.') % self.object.name,
        )
        return super().form_valid(form)


class CustomerQuickCreateView(LoginRequiredMixin, CreateView):
    """
    Create a customer via AJAX for the Point of Sale interface.

    For AJAX requests (X-Requested-With: XMLHttpRequest), returns a JSON
    response with success/error details. For regular requests, behaves like
    a normal CreateView.
    """

    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'

    def is_ajax(self):
        """Check whether the current request is an AJAX request."""
        return self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def form_valid(self, form):
        """Save the customer and return JSON or redirect based on request type."""
        self.object = form.save()

        if self.is_ajax():
            return JsonResponse({
                'success': True,
                'customer': {
                    'id': self.object.pk,
                    'name': self.object.name,
                    'phone': self.object.phone,
                },
            })

        messages.success(
            self.request,
            _('Customer "%s" created successfully.') % self.object.name,
        )
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        """Return JSON errors or re-render the form based on request type."""
        if self.is_ajax():
            return JsonResponse({
                'success': False,
                'errors': json.loads(
                    json.dumps(form.errors)
                ),
            }, status=400)

        return super().form_invalid(form)

    def get_success_url(self):
        """Redirect to the customer detail view on success."""
        return reverse_lazy('customers:customer_detail', kwargs={'pk': self.object.pk})