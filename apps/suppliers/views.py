"""
MediPOS Suppliers — Views.

Class-based views for Supplier management, including CSV bulk import.
All views require authentication; Admin & Pharmacist roles get full access,
Cashier is read-only.
"""
import csv
import io

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)

from .forms import SupplierForm, SupplierImportForm
from .models import Supplier


# ═══════════════════════════════════════════════════════════════════════════════
# Mixins
# ═══════════════════════════════════════════════════════════════════════════════


class StaffEditorMixin(UserPassesTestMixin):
    """
    Mixin that restricts access to Admin and Pharmacist roles.

    Cashier users will receive a 403 Forbidden response with an error message.
    """

    def test_func(self):
        """Allow only Admin and Pharmacist roles."""
        user = self.request.user
        return user.is_authenticated and user.role in ('ADMIN', 'PHARMACIST')

    def handle_no_permission(self):
        """Show an error message and redirect to the supplier list."""
        messages.error(
            self.request,
            _("You don't have permission to perform this action."),
        )
        return redirect('suppliers:supplier_list')


# ═══════════════════════════════════════════════════════════════════════════════
# Supplier Views
# ═══════════════════════════════════════════════════════════════════════════════


class SupplierListView(LoginRequiredMixin, ListView):
    """
    Display a paginated, searchable list of all suppliers.

    Supports search by name, phone, or contact person via GET parameter 'q'.
    """

    model = Supplier
    template_name = 'suppliers/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 25
    ordering = ['name']

    def get_queryset(self):
        """Optionally filter by search query across name, phone, and contact person."""
        queryset = Supplier.objects.all()
        search = self.request.GET.get('q', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(phone__icontains=search)
                | Q(contact_person__icontains=search)
            )
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        """Add the search query string to template context."""
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q', '').strip()
        return context


class SupplierDetailView(LoginRequiredMixin, DetailView):
    """
    Display the full details of a single supplier.

    Shows all fields, balance, active status badge, and payment
    transaction history.
    """

    model = Supplier
    template_name = 'suppliers/supplier_detail.html'
    context_object_name = 'supplier'

    def get_object(self, queryset=None):
        """Fetch the supplier or return a 404."""
        return get_object_or_404(Supplier, pk=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        """Add recent payment transactions to the context."""
        context = super().get_context_data(**kwargs)
        from apps.payments.models import PaymentTransaction
        from django.contrib.contenttypes.models import ContentType
        supplier_ct = ContentType.objects.get_for_model(Supplier)
        context['transactions'] = PaymentTransaction.objects.filter(
            content_type=supplier_ct,
            object_id=self.object.pk,
        ).select_related('created_by').order_by('-created_at')[:10]
        return context


class SupplierCreateView(LoginRequiredMixin, StaffEditorMixin, CreateView):
    """
    Create a new supplier record.

    Displays a success message and redirects to the supplier detail view.
    """

    model = Supplier
    form_class = SupplierForm
    template_name = 'suppliers/supplier_form.html'

    def form_valid(self, form):
        """Add a success message after creating the supplier."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            _('Supplier "%s" created successfully.') % self.object.name,
        )
        return response


class SupplierUpdateView(LoginRequiredMixin, StaffEditorMixin, UpdateView):
    """
    Update an existing supplier record.

    Displays a success message and redirects to the supplier detail view.
    """

    model = Supplier
    form_class = SupplierForm
    template_name = 'suppliers/supplier_form.html'

    def form_valid(self, form):
        """Add a success message after updating the supplier."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            _('Supplier "%s" updated successfully.') % self.object.name,
        )
        return response


class SupplierDeleteView(LoginRequiredMixin, StaffEditorMixin, DeleteView):
    """
    Permanently delete a supplier from the database.

    Confirms with the user before deleting. Redirects to the supplier list.
    """

    model = Supplier
    template_name = 'suppliers/supplier_confirm_delete.html'
    success_url = reverse_lazy('suppliers:supplier_list')

    def get_object(self, queryset=None):
        """Fetch the supplier or return a 404."""
        return get_object_or_404(Supplier, pk=self.kwargs.get('pk'))

    def form_valid(self, form):
        """Hard-delete: permanently remove the supplier record."""
        messages.success(
            self.request,
            _('Supplier "%s" deleted successfully.') % self.object.name,
        )
        return super().form_valid(form)


# ═══════════════════════════════════════════════════════════════════════════════
# Bulk Import View
# ═══════════════════════════════════════════════════════════════════════════════


class SupplierBulkImportView(LoginRequiredMixin, StaffEditorMixin, FormView):
    """
    Bulk import suppliers from a CSV file.

    GET: Renders the upload form with a download template link.
    POST: Parses the CSV, validates each row, and creates Supplier objects
          in bulk using bulk_create with batch_size=500.
          Reports success count and row-level errors via messages.
    """

    template_name = 'suppliers/supplier_import.html'
    form_class = SupplierImportForm
    success_url = reverse_lazy('suppliers:supplier_list')

    # Expected CSV columns (in order)
    CSV_COLUMNS = [
        'name',
        'contact_person',
        'phone',
        'email',
        'address',
        'notes',
    ]

    def form_valid(self, form):
        """
        Process the uploaded CSV file and create Supplier objects.

        Returns:
            HTTP redirect to the supplier list on completion.
        """
        csv_file = form.cleaned_data['csv_file']
        raw_data = csv_file.read()
        try:
            decoded_file = raw_data.decode('utf-8-sig')
        except UnicodeDecodeError:
            decoded_file = raw_data.decode('latin-1')
        reader = csv.DictReader(io.StringIO(decoded_file))

        success_count = 0
        errors = []
        suppliers_to_create = []

        for row_num, row in enumerate(reader, start=2):  # Start at 2 to skip header
            # Skip empty rows
            if not any(row.values()):
                continue

            name = row.get('name', '').strip()
            if not name:
                errors.append(_('Row %(row)d: Name is required.') % {'row': row_num})
                continue

            phone = row.get('phone', '').strip()
            if not phone:
                errors.append(
                    _('Row %(row)d (%(name)s): Phone is required.')
                    % {'row': row_num, 'name': name},
                )
                continue

            # Check for duplicate phone number
            existing = Supplier.objects.filter(phone__iexact=phone).first()
            if existing:
                errors.append(
                    _('Row %(row)d (%(name)s): Phone "%(phone)s" already exists.')
                    % {'row': row_num, 'name': name, 'phone': phone},
                )
                continue

            suppliers_to_create.append(
                Supplier(
                    name=name,
                    contact_person=row.get('contact_person', '').strip(),
                    phone=phone,
                    email=row.get('email', '').strip(),
                    address=row.get('address', '').strip(),
                    notes=row.get('notes', '').strip(),
                )
            )

        # Bulk create suppliers
        if suppliers_to_create:
            try:
                Supplier.objects.bulk_create(suppliers_to_create, batch_size=500)
                success_count = len(suppliers_to_create)
            except Exception as exc:
                errors.append(
                    _('Database error during import: %(error)s.')
                    % {'error': exc},
                )

        # Show a consolidated success message
        if success_count:
            messages.success(
                self.request,
                _('%(count)d supplier(s) imported successfully.')
                % {'count': success_count},
            )

        # Show error messages
        if errors:
            # Attach errors to session so template can display them
            # Coerce lazy translation proxies to plain strings for JSON
            # serialization (Django's default session serializer).
            self.request.session['import_errors'] = [str(e) for e in errors]
            messages.warning(
                self.request,
                _(
                    'Import completed with %(error_count)d error(s). '
                    'See details below.'
                )
                % {'error_count': len(errors)},
            )
        elif not success_count:
            messages.warning(
                self.request,
                _('No suppliers were imported. Please check your CSV file.'),
            )

        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        """
        Add import errors from session to context and clear them after reading.
        """
        context = super().get_context_data(**kwargs)
        context['import_errors'] = self.request.session.pop('import_errors', [])
        return context


# ═══════════════════════════════════════════════════════════════════════════════
# Template Download View
# ═══════════════════════════════════════════════════════════════════════════════


def download_supplier_template(request):
    """
    Serve the CSV import template for suppliers as a downloadable file.

    The template contains the header row with all expected columns.
    """
    template_path = 'static/files/supplier_import_template.csv'
    try:
        from django.conf import settings

        file_path = settings.BASE_DIR / template_path
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        # Fallback: generate header row
        content = 'name,contact_person,phone,email,address,notes\n'
    response = HttpResponse(content, content_type='text/csv')
    response['Content-Disposition'] = (
        'attachment; filename="supplier_import_template.csv"'
    )
    return response
