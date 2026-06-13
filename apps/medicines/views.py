"""
MediPOS Medicines — Views.

Class-based views for Category and Medicine management, including
CSV bulk import. All views require authentication; Admin & Pharmacist
roles get full access, Cashier is read-only.
"""
import csv
import io

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, F, Q
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)

from .filters import MedicineFilter
from .forms import CategoryForm, CategoryImportForm, GenericNameForm, MedicineForm, MedicineImportForm
from .models import Category, GenericName, Medicine


# ═══════════════════════════════════════════════════════════════════════════════
# Mixins
# ═══════════════════════════════════════════════════════════════════════════════


class StaffEditorMixin(UserPassesTestMixin):
    """
    Mixin that restricts access to Admin and Pharmacist roles.

    Cashier users will see a 403 Forbidden response.
    """

    def test_func(self):
        """Allow only Admin and Pharmacist roles."""
        user = self.request.user
        return user.is_authenticated and user.role in ('ADMIN', 'PHARMACIST')

    def handle_no_permission(self):
        """Show an error message and redirect to the medicine list."""
        messages.error(self.request, _('You do not have permission to perform this action.'))
        return redirect('medicines:medicine_list')


# ═══════════════════════════════════════════════════════════════════════════════
# Category Views
# ═══════════════════════════════════════════════════════════════════════════════


class CategoryListView(LoginRequiredMixin, ListView):
    """
    Display a paginated list of all categories.

    Supports search by category name via GET parameter 'q'.
    """

    model = Category
    template_name = 'medicines/category_list.html'
    context_object_name = 'categories'
    paginate_by = 25

    def get_queryset(self):
        """Optionally filter by search query on category name."""
        queryset = Category.objects.all()
        search = self.request.GET.get('q', '').strip()
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

    def get_context_data(self, **kwargs):
        """Add search query to context for template rendering."""
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q', '').strip()
        return context


class CategoryCreateView(LoginRequiredMixin, StaffEditorMixin, CreateView):
    """
    Create a new product category.

    Displays a success message upon creation and redirects to the category list.
    """

    model = Category
    form_class = CategoryForm
    template_name = 'medicines/category_form.html'

    def form_valid(self, form):
        """Add a success message after creating the category."""
        response = super().form_valid(form)
        messages.success(self.request, _(f'Category "{self.object.name}" created successfully.'))
        return response

    def get_success_url(self):
        """Redirect to the category list."""
        return reverse_lazy('medicines:category_list')


class CategoryUpdateView(LoginRequiredMixin, StaffEditorMixin, UpdateView):
    """
    Update an existing product category identified by its slug.

    Displays a success message upon update and redirects to the category list.
    """

    model = Category
    form_class = CategoryForm
    template_name = 'medicines/category_form.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def form_valid(self, form):
        """Add a success message after updating the category."""
        response = super().form_valid(form)
        messages.success(self.request, _(f'Category "{self.object.name}" updated successfully.'))
        return response

    def get_success_url(self):
        """Redirect to the category list."""
        return reverse_lazy('medicines:category_list')


class CategoryDeleteView(LoginRequiredMixin, StaffEditorMixin, DeleteView):
    """
    Delete a product category identified by its slug.

    Warns if medicines are linked to this category; deletes only if confirmed.
    Displays a success message and redirects to the category list.
    """

    model = Category
    template_name = 'medicines/category_confirm_delete.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('medicines:category_list')

    def get_context_data(self, **kwargs):
        """Add the count of linked medicines for the warning."""
        context = super().get_context_data(**kwargs)
        context['linked_count'] = self.object.medicines.count()
        return context

    def form_valid(self, form):
        """Add a success message after deleting the category."""
        name = self.object.name
        response = super().form_valid(form)
        messages.success(self.request, _(f'Category "{name}" deleted successfully.'))
        return response


# ═══════════════════════════════════════════════════════════════════════════════
# Generic Name Views
# ═══════════════════════════════════════════════════════════════════════════════


class GenericNameListView(LoginRequiredMixin, ListView):
    model = GenericName
    template_name = 'medicines/generic_name_list.html'
    context_object_name = 'generic_names'
    paginate_by = 50

    def get_queryset(self):
        queryset = GenericName.objects.annotate(
            medicine_count=Count('medicines')
        )
        search = self.request.GET.get('q', '').strip()
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q', '').strip()
        return context

    def render_to_response(self, context, **kwargs):
        if self.request.GET.get('partial') == '1':
            from django.template.loader import render_to_string
            from django.http import JsonResponse
            html = render_to_string(
                'medicines/generic_name_table.html',
                context,
                request=self.request,
            )
            pg = context['page_obj']
            return JsonResponse({
                'html': html,
                'total': pg.paginator.count,
                'page_info': f'Page {pg.number} of {pg.paginator.num_pages}',
            })
        return super().render_to_response(context, **kwargs)


class GenericNameCreateView(LoginRequiredMixin, StaffEditorMixin, CreateView):
    model = GenericName
    form_class = GenericNameForm
    template_name = 'medicines/generic_name_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _(f'Generic name "{self.object.name}" created successfully.'))
        return response

    def get_success_url(self):
        return reverse_lazy('medicines:generic_name_list')


class GenericNameUpdateView(LoginRequiredMixin, StaffEditorMixin, UpdateView):
    model = GenericName
    form_class = GenericNameForm
    template_name = 'medicines/generic_name_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _(f'Generic name "{self.object.name}" updated successfully.'))
        return response

    def get_success_url(self):
        return reverse_lazy('medicines:generic_name_list')


class GenericNameDeleteView(LoginRequiredMixin, StaffEditorMixin, DeleteView):
    model = GenericName
    template_name = 'medicines/generic_name_confirm_delete.html'
    success_url = reverse_lazy('medicines:generic_name_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['linked_count'] = self.object.medicines.count()
        return context

    def form_valid(self, form):
        name = self.object.name
        response = super().form_valid(form)
        messages.success(self.request, _(f'Generic name "{name}" deleted successfully.'))
        return response


# ═══════════════════════════════════════════════════════════════════════════════
# Medicine Views
# ═══════════════════════════════════════════════════════════════════════════════


class MedicineListView(LoginRequiredMixin, ListView):
    """
    Display a paginated, filterable list of all medicines.

    Supports django-filter for search, category, active status, and low-stock.
    """

    model = Medicine
    template_name = 'medicines/medicine_list.html'
    context_object_name = 'medicines'
    paginate_by = 25

    def get_queryset(self):
        """Apply medicine filters from the MedicineFilter FilterSet."""
        queryset = Medicine.objects.select_related('category').all()
        self.filterset = MedicineFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        """Add the filterset and low-stock count to the template context."""
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset
        context['low_stock_count'] = Medicine.objects.filter(
            stock_quantity__lte=F('reorder_level')
        ).count()
        return context


class MedicineDetailView(LoginRequiredMixin, DetailView):
    """
    Display the full details of a single medicine.

    Shows all fields, stock status badge, profit margin, and action buttons.
    """

    model = Medicine
    template_name = 'medicines/medicine_detail.html'
    context_object_name = 'medicine'


class MedicineCreateView(LoginRequiredMixin, StaffEditorMixin, CreateView):
    """
    Create a new medicine record.

    Displays a success message and redirects to the medicine detail view.
    """

    model = Medicine
    form_class = MedicineForm
    template_name = 'medicines/medicine_form.html'

    def form_valid(self, form):
        """Add a success message after creating the medicine."""
        response = super().form_valid(form)
        messages.success(self.request, _(f'Medicine "{self.object.name}" created successfully.'))
        return response


class MedicineUpdateView(LoginRequiredMixin, StaffEditorMixin, UpdateView):
    """
    Update an existing medicine record.

    Displays a success message and redirects to the medicine detail view.
    """

    model = Medicine
    form_class = MedicineForm
    template_name = 'medicines/medicine_form.html'

    def form_valid(self, form):
        """Add a success message after updating the medicine."""
        response = super().form_valid(form)
        messages.success(self.request, _(f'Medicine "{self.object.name}" updated successfully.'))
        return response


class MedicineDeleteView(LoginRequiredMixin, StaffEditorMixin, DeleteView):
    """
    Soft-delete a medicine by setting is_active=False.

    Confirms with the user before deactivating. Redirects to the medicine list.
    """

    model = Medicine
    template_name = 'medicines/medicine_confirm_delete.html'
    success_url = reverse_lazy('medicines:medicine_list')

    def _deactivate(self):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save(update_fields=['is_active'])
        messages.success(
            self.request,
            _(f'Medicine "{self.object.name}" has been deactivated.'),
        )

    def delete(self, request, *args, **kwargs):
        """Soft-delete for Django < 4.0 (post → delete)."""
        self._deactivate()
        return redirect(self.success_url)

    def form_valid(self, form):
        """Soft-delete for Django >= 4.0 (post → form_valid)."""
        self._deactivate()
        return redirect(self.success_url)


class MedicineBulkImportView(LoginRequiredMixin, StaffEditorMixin, FormView):
    """
    Bulk import medicines from a CSV file.

    GET: Renders the upload form with a download template link.
    POST: Parses the CSV, validates each row, and creates Medicine objects
          in bulk using bulk_create with batch_size=500.
          Reports success count and row-level errors via messages.
    """

    template_name = 'medicines/medicine_import.html'
    form_class = MedicineImportForm
    success_url = reverse_lazy('medicines:medicine_list')

    # Expected CSV columns (in order)
    CSV_COLUMNS = [
        'name',
        'generic_name',
        'brand',
        'category',
        'barcode',
        'unit',
        'purchase_price',
        'selling_price',
        'tax_rate',
        'reorder_level',
        'description',
    ]

    def form_valid(self, form):
        """
        Process the uploaded CSV file and create Medicine objects.

        Returns:
            HTTP redirect to the medicine list on completion.
        """
        csv_file = form.cleaned_data['csv_file']
        decoded_file = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded_file))

        success_count = 0
        errors = []
        medicines_to_create = []

        for row_num, row in enumerate(reader, start=2):  # Start at 2 to skip header
            # Skip empty rows
            if not any(row.values()):
                continue

            name = row.get('name', '').strip()
            if not name:
                errors.append(_(f'Row {row_num}: Name is required.'))
                continue

            # Validate required numeric fields
            try:
                purchase_price = float(row.get('purchase_price', 0) or 0)
                selling_price = float(row.get('selling_price', 0) or 0)
                tax_rate = float(row.get('tax_rate', 15) or 15)
                reorder_level = int(row.get('reorder_level', 10) or 10)
            except (ValueError, TypeError) as exc:
                errors.append(_(f'Row {row_num} ({name}): Invalid numeric value — {exc}.'))
                continue

            barcode = row.get('barcode', '').strip() or None

            # Check for duplicate barcode
            if barcode:
                existing = Medicine.objects.filter(barcode=barcode).first()
                if existing:
                    errors.append(
                        _(f'Row {row_num} ({name}): Barcode "{barcode}" already exists.'),
                    )
                    continue

            # Resolve category by name
            category_name = row.get('category', '').strip()
            category = None
            if category_name:
                try:
                    category = Category.objects.get(name__iexact=category_name)
                except Category.DoesNotExist:
                    errors.append(
                        _(f'Row {row_num} ({name}): Category "{category_name}" not found.'),
                    )
                    continue

            medicines_to_create.append(
                Medicine(
                    name=name,
                    generic_name=row.get('generic_name', '').strip(),
                    brand=row.get('brand', '').strip(),
                    category=category,
                    barcode=barcode,
                    unit=row.get('unit', 'Pcs').strip() or 'Pcs',
                    purchase_price=purchase_price,
                    selling_price=selling_price,
                    tax_rate=tax_rate,
                    reorder_level=reorder_level,
                    description=row.get('description', '').strip(),
                )
            )

        # Bulk create medicines
        if medicines_to_create:
            try:
                Medicine.objects.bulk_create(medicines_to_create, batch_size=500)
                success_count = len(medicines_to_create)
            except Exception as exc:
                errors.append(_(f'Database error during import: {exc}.'))

        # Show a consolidated success message
        if success_count:
            messages.success(
                self.request,
                _('%(count)d medicine(s) imported successfully.')
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
                _('No medicines were imported. Please check your CSV file.'),
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
# Category Bulk Import View
# ═══════════════════════════════════════════════════════════════════════════════


class CategoryBulkImportView(LoginRequiredMixin, StaffEditorMixin, FormView):
    """
    Bulk import categories from a CSV file.

    GET: Renders the upload form with a download template link.
    POST: Parses the CSV, validates each row, and creates Category objects
          in bulk using bulk_create.
          Reports success count and row-level errors via messages.
    """

    template_name = 'medicines/category_import.html'
    form_class = CategoryImportForm
    success_url = reverse_lazy('medicines:category_list')

    # Expected CSV columns (in order)
    CSV_COLUMNS = ['name', 'description', 'is_active']

    def form_valid(self, form):
        """
        Process the uploaded CSV file and create Category objects.

        Returns:
            HTTP redirect to the category list on completion.
        """
        csv_file = form.cleaned_data['csv_file']
        decoded_file = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded_file))

        success_count = 0
        errors = []
        categories_to_create = []

        for row_num, row in enumerate(reader, start=2):  # Start at 2 to skip header
            # Skip empty rows
            if not any(row.values()):
                continue

            name = row.get('name', '').strip()
            if not name:
                errors.append(_(f'Row {row_num}: Name is required.'))
                continue

            # Check for duplicate category name (case-insensitive)
            if Category.objects.filter(name__iexact=name).exists():
                errors.append(
                    _(f'Row {row_num} ({name}): Category already exists.'),
                )
                continue

            # Parse optional fields
            description = row.get('description', '').strip()
            is_active_str = row.get('is_active', 'true').strip().lower()
            is_active = is_active_str in ('true', '1', 'yes', 'y')

            categories_to_create.append(
                Category(
                    name=name,
                    slug=slugify(name),
                    description=description,
                    is_active=is_active,
                )
            )

        # Bulk create categories
        if categories_to_create:
            try:
                Category.objects.bulk_create(categories_to_create, batch_size=500)
                success_count = len(categories_to_create)
            except Exception as exc:
                errors.append(_(f'Database error during import: {exc}.'))

        # Show a consolidated success message
        if success_count:
            messages.success(
                self.request,
                _('%(count)d category/categories imported successfully.')
                % {'count': success_count},
            )

        # Show error messages
        if errors:
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
                _('No categories were imported. Please check your CSV file.'),
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


def download_import_template(request):
    """
    Serve the CSV import template as a downloadable file.

    The template contains the header row with all expected columns.
    """
    template_path = 'static/files/medicine_import_template.csv'
    try:
        from django.conf import settings
        file_path = settings.BASE_DIR / template_path
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        # Fallback: generate header row
        content = (
            'name,generic_name,brand,category,barcode,unit,'
            'purchase_price,selling_price,tax_rate,reorder_level,description\n'
        )
    response = HttpResponse(content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="medicine_import_template.csv"'
    return response


def download_category_import_template(request):
    """
    Serve the category CSV import template as a downloadable file.

    The template contains the header row with all expected columns.
    """
    template_path = 'static/files/category_import_template.csv'
    try:
        from django.conf import settings
        file_path = settings.BASE_DIR / template_path
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        # Fallback: generate header row
        content = 'name,description,is_active\n'
    response = HttpResponse(content, content_type='text/csv')
    response['Content-Disposition'] = (
        'attachment; filename="category_import_template.csv"'
    )
    return response


# ═══════════════════════════════════════════════════════════════════════════════
# AJAX Search Views — for medicine_form.html search widgets
# ═══════════════════════════════════════════════════════════════════════════════


class GenericNameSearchView(LoginRequiredMixin, View):
    """Return matching GenericName records as JSON for the medicine form search widget."""

    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'results': []})
        qs = GenericName.objects.filter(name__icontains=query).order_by('name')[:30]
        return JsonResponse({'results': [{'id': g.pk, 'name': g.name} for g in qs]})


class CategorySearchView(LoginRequiredMixin, View):
    """Return matching active Category records as JSON for the medicine form search widget."""

    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'results': []})
        qs = Category.objects.filter(is_active=True, name__icontains=query).order_by('name')[:30]
        return JsonResponse({'results': [{'id': c.pk, 'name': c.name} for c in qs]})


class BrandSearchView(LoginRequiredMixin, View):
    """Return distinct brand values matching query as JSON for the medicine form search widget."""

    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'results': []})
        brands = (
            Medicine.objects
            .filter(brand__icontains=query)
            .exclude(brand='')
            .values_list('brand', flat=True)
            .distinct()
            .order_by('brand')[:30]
        )
        return JsonResponse({'results': [{'name': b} for b in brands]})


class MedicinesByCategoryView(LoginRequiredMixin, View):
    """Return medicines filtered by category as JSON."""

    def get(self, request):
        category_id = request.GET.get('category_id', '').strip()
        if not category_id:
            return JsonResponse({'results': []})
        qs = Medicine.objects.filter(
            is_active=True, category_id=category_id
        ).order_by('name').values('id', 'name')[:100]
        return JsonResponse({'results': list(qs)})


class MedicineSearchView(LoginRequiredMixin, View):
    """Return medicines matching a name query as JSON, optionally filtered by category."""

    def get(self, request):
        query = request.GET.get('q', '').strip()
        category_id = request.GET.get('category_id', '').strip()
        if not query:
            return JsonResponse({'results': []})
        qs = Medicine.objects.filter(is_active=True, name__icontains=query)
        if category_id:
            qs = qs.filter(category_id=category_id)
        qs = qs.order_by('name').values('id', 'name')[:30]
        return JsonResponse({'results': list(qs)})
