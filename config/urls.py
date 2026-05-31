"""
MediPOS URL Configuration.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import DashboardView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Accounts (auth, profile, etc.)
    path('accounts/', include('apps.accounts.urls')),

    # Dashboard
    path('', DashboardView.as_view(), name='dashboard'),

    # Medicines (Product / Category management)
    path('medicines/', include('apps.medicines.urls')),

    # Suppliers (Vendor management)
    path('suppliers/', include('apps.suppliers.urls')),

    # Inventory (Batch tracking, Stock Ledger, Adjustments)
    path('inventory/', include('apps.inventory.urls')),

    # Customers
    path('customers/', include('apps.customers.urls')),

    # Sales (POS, Invoices)
    path('sales/', include('apps.sales.urls')),

    # Purchases
    path('purchases/', include('apps.purchases.urls')),

    # Returns
    path('returns/', include('apps.returns.urls')),

    # Reports
    path('reports/', include('apps.reports.urls')),

    # Settings (Admin only)
    path('settings/', include('apps.settings.urls')),

    # Payments (Dues & Advances for Customers/Suppliers)
    path('payments/', include('apps.payments.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)