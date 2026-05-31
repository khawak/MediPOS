"""
MediPOS Accounts — Views.

Class-based views for authentication, user management, profile handling,
and the dashboard.
All views (except login/logout) require authentication. Admin-only views
additionally require appropriate permissions.
"""
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    LoginForm,
    PasswordChangeForm,
    ProfileUpdateForm,
    UserCreateForm,
    UserEditForm,
)
from .models import User


# ═══════════════════════════════════════════════════════════════════════════
# Authentication Views
# ═══════════════════════════════════════════════════════════════════════════


class LoginView(auth_views.LoginView):
    """
    Custom login view for MediPOS.

    Renders a centered login card with MediPOS branding.
    Displays a success message on login via form_valid.
    """

    template_name = 'accounts/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        """Add a success message when the user logs in successfully."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            _(f'Welcome back, {self.request.user.get_full_name() or self.request.user.username}!'),
        )
        return response


class LogoutView(auth_views.LogoutView):
    """
    Custom logout view for MediPOS.

    Redirects to the login page and displays a logout confirmation message.
    """

    next_page = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        """Add a logout message before processing the logout."""
        messages.info(request, _('You have been logged out successfully.'))
        return super().dispatch(request, *args, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════
# User Management Views (Admin Only)
# ═══════════════════════════════════════════════════════════════════════════


class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Display a paginated, searchable list of all users.

    Accessible only to users with the 'accounts.view_user' permission
    (granted to the Admin role via group permissions).
    """

    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 25
    permission_required = 'accounts.view_user'
    raise_exception = True

    def get_queryset(self):
        """
        Return filtered and ordered queryset of users.

        Supports search by username, email, first name, or last name.
        Uses select_related to minimize queries (User has no FK relationships,
        but this keeps the pattern consistent).
        """
        queryset = User.objects.all().order_by('-date_joined')
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        """Add search query and role choices to template context."""
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '').strip()
        context['role_choices'] = User.Role.choices
        return context


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Create a new user (admin-only).

    Accessible only to users with the 'accounts.add_user' permission.
    """

    model = User
    form_class = UserCreateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')
    permission_required = 'accounts.add_user'
    raise_exception = True

    def form_valid(self, form):
        """Add a success message after creating the user."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            _(f'User "{self.object.username}" has been created successfully.'),
        )
        return response

    def get_context_data(self, **kwargs):
        """Indicate to the template that this is a create action."""
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        context['page_title'] = _('Add New User')
        return context


class UserDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Display detailed information about a specific user (admin-only).

    Accessible only to users with the 'accounts.view_user' permission.
    """

    model = User
    template_name = 'accounts/user_detail.html'
    context_object_name = 'profile_user'
    permission_required = 'accounts.view_user'
    raise_exception = True

    def get_object(self, queryset=None):
        """Retrieve the user by primary key, or return a 404."""
        return get_object_or_404(User, pk=self.kwargs['pk'])


class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Edit an existing user's details (admin-only).

    Accessible only to users with the 'accounts.change_user' permission.
    """

    model = User
    form_class = UserEditForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')
    permission_required = 'accounts.change_user'
    raise_exception = True

    def get_object(self, queryset=None):
        """Retrieve the user by primary key, or return a 404."""
        return get_object_or_404(User, pk=self.kwargs['pk'])

    def form_valid(self, form):
        """Add a success message after updating the user."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            _(f'User "{self.object.username}" has been updated successfully.'),
        )
        return response

    def get_context_data(self, **kwargs):
        """Indicate to the template that this is an edit action."""
        context = super().get_context_data(**kwargs)
        context['action'] = 'Edit'
        context['page_title'] = _(f'Edit User: {self.object.username}')
        return context


class UserDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Soft-delete (deactivate) a user (admin-only).

    Instead of permanently deleting the user, sets is_active to False.
    Accessible only to users with the 'accounts.delete_user' permission.
    """

    model = User
    template_name = 'accounts/user_confirm_delete.html'
    context_object_name = 'profile_user'
    success_url = reverse_lazy('accounts:user_list')
    permission_required = 'accounts.delete_user'
    raise_exception = True

    def get_object(self, queryset=None):
        """Retrieve the user by primary key, or return a 404."""
        return get_object_or_404(User, pk=self.kwargs['pk'])

    def form_valid(self, form):
        """
        Soft-delete by setting is_active to False instead of hard-deleting.

        This preserves data integrity and allows for potential reactivation.
        """
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=['is_active'])
        messages.warning(
            self.request,
            _(f'User "{user.username}" has been deactivated.'),
        )
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(self.success_url)


# ═══════════════════════════════════════════════════════════════════════════
# Profile Views (Any Authenticated User)
# ═══════════════════════════════════════════════════════════════════════════


class ProfileView(LoginRequiredMixin, DetailView):
    """
    Display the logged-in user's own profile.

    This is the default view any authenticated user can access to see
    their profile information.
    """

    model = User
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'

    def get_object(self, queryset=None):
        """Return the currently logged-in user."""
        return self.request.user


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """
    Allow the logged-in user to edit their own profile.

    Users can update their name, email, phone, and avatar. Role and
    active status fields are excluded from the form for security.
    """

    model = User
    form_class = ProfileUpdateForm
    template_name = 'accounts/profile_form.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        """Return the currently logged-in user."""
        return self.request.user

    def form_valid(self, form):
        """Add a success message after updating the profile."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            _('Your profile has been updated successfully.'),
        )
        return response


# ═══════════════════════════════════════════════════════════════════════════
# Password Change Views
# ═══════════════════════════════════════════════════════════════════════════


class PasswordChangeView(LoginRequiredMixin, auth_views.PasswordChangeView):
    """
    Allow the logged-in user to change their password.

    Uses Bootstrap 5 styling via crispy-forms and redirects to a
    success confirmation page.
    """

    form_class = PasswordChangeForm
    template_name = 'accounts/password_change_form.html'
    success_url = reverse_lazy('accounts:password_change_done')


class PasswordChangeDoneView(LoginRequiredMixin, auth_views.PasswordChangeDoneView):
    """
    Confirmation page displayed after a successful password change.

    Simply renders a success message confirming the password was changed.
    """

    template_name = 'accounts/password_change_done.html'


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard View
# ═══════════════════════════════════════════════════════════════════════════


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Main dashboard view showing key business metrics.

    Provides aggregated stats for today's sales, inventory health,
    expiring batches, and recent transactions.
    """

    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        """Augment the template context with live dashboard statistics."""
        from apps.inventory.models import Batch
        from apps.medicines.models import Medicine
        from apps.sales.models import Sale

        context = super().get_context_data(**kwargs)
        today = date.today()

        # Today's sales KPIs
        today_sales_qs = Sale.objects.filter(
            sale_date__date=today,
            status=Sale.Status.COMPLETED,
        )
        context['today_sales_count'] = today_sales_qs.count()
        context['today_sales_amount'] = (
            today_sales_qs.aggregate(total=Sum('grand_total'))['total'] or 0
        )

        # Medicine counts
        active_medicines = Medicine.objects.filter(is_active=True)
        context['total_medicines'] = active_medicines.count()
        context['low_stock_count'] = active_medicines.filter(
            stock_quantity__lte=F('reorder_level'),
        ).count()

        # Expiring within 30 days
        cutoff_date = today + timedelta(days=30)
        context['expiring_soon_count'] = Batch.objects.filter(
            expiry_date__lte=cutoff_date,
            expiry_date__gte=today,
            quantity__gt=0,
        ).count()

        # Recent sales (last 10)
        context['recent_sales'] = Sale.objects.filter(
            status=Sale.Status.COMPLETED,
        ).order_by('-sale_date')[:10]

        # Low stock medicines (top 5)
        context['low_stock_medicines'] = active_medicines.filter(
            stock_quantity__lte=F('reorder_level'),
        )[:5]

        return context