"""
MediPOS Settings — Views.

Provides views for editing shop settings and performing database backups.
Both views are restricted to Admin-role users only.
"""
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, UpdateView, View

from .forms import ShopSettingsForm
from .models import ShopSettings


# ═══════════════════════════════════════════════════════════════════════════
# Admin-Only Access Mixin
# ═══════════════════════════════════════════════════════════════════════════


class AdminRequiredMixin(LoginRequiredMixin):
    """
    Restrict access to users with the ADMIN role only.

    Non-admin users receive a 404 (not found) response to avoid
    revealing the existence of admin-only URLs.
    """

    def dispatch(self, request, *args, **kwargs):
        """Check if the authenticated user has the ADMIN role."""
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role != 'ADMIN':
            raise Http404()
        return super().dispatch(request, *args, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════
# Shop Settings View
# ═══════════════════════════════════════════════════════════════════════════


class SettingsUpdateView(AdminRequiredMixin, UpdateView):
    """
    View for updating the singleton ShopSettings instance.

    Only accessible by Admin-role users.  Always edits the singleton
    (pk=1), which is auto-created if it doesn't exist.
    """

    form_class = ShopSettingsForm
    template_name = 'settings/settings_form.html'
    success_url = reverse_lazy('settings:settings_update')

    def get_object(self, queryset=None):
        """Return the singleton ShopSettings instance."""
        return ShopSettings.get_settings()

    def form_valid(self, form):
        """Add a success message after saving settings."""
        messages.success(self.request, _('Shop settings have been updated successfully.'))
        return super().form_valid(form)


# ═══════════════════════════════════════════════════════════════════════════
# Database Backup View
# ═══════════════════════════════════════════════════════════════════════════


class BackupDatabaseView(AdminRequiredMixin, View):
    """
    View for creating and downloading database backups.

    GET  — displays a page listing previous backup files.
    POST — creates a new SQLite backup file and serves it as a download.

    Backups are stored in MEDIA_ROOT/backups/.
    """

    template_name = 'settings/backup.html'

    def get(self, request, *args, **kwargs):
        """Render the backup page with a list of existing backup files."""
        from django.template.response import TemplateResponse

        backup_dir = Path(django_settings.MEDIA_ROOT) / 'backups'
        backup_files = []
        if backup_dir.exists():
            backup_files = sorted(
                backup_dir.glob('backup-*.sqlite3'),
                reverse=True,
            )
            backup_files = [
                {
                    'name': f.name,
                    'size': f.stat().st_size,
                    'modified': datetime.fromtimestamp(f.stat().st_mtime),
                }
                for f in backup_files
            ]

        context = {
            'backup_files': backup_files,
        }
        return TemplateResponse(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """Create a backup of the SQLite database and serve it as a download."""
        # Determine source and destination paths
        db_path = Path(django_settings.DATABASES['default']['NAME'])
        backup_dir = Path(django_settings.MEDIA_ROOT) / 'backups'
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
        backup_filename = f'backup-{timestamp}.sqlite3'
        backup_path = backup_dir / backup_filename

        # Copy the database file
        shutil.copy2(db_path, backup_path)

        # Serve the file as a download
        with open(backup_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{backup_filename}"'
            response['Content-Length'] = backup_path.stat().st_size

        messages.success(
            request,
            _(f'Database backup created successfully: {backup_filename}'),
        )
        return response