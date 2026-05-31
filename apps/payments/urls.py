"""
MediPOS Payments — URL Configuration.
"""
from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    # Due Management Dashboard
    path('dues/', views.DueManagementDashboardView.as_view(),name='due_dashboard',
    ),

    # Customer Dues List
    path( 'dues/customers/', views.CustomerDueListView.as_view(), name='customer_dues',
    ),

    # Supplier Dues List
    path('dues/suppliers/', views.SupplierDueListView.as_view(),name='supplier_dues',
    ),

    # Settle dues for a specific customer or supplier
    path( 'dues/settle/<slug:content_type_slug>/<int:object_id>/',views.DueSettleView.as_view(),name='due_settle',
    ),

    # List all payment transactions
    path('', views.PaymentTransactionListView.as_view(), name='payment_list'),

    # Record a payment/advance for a customer or supplier
    # /payments/add/customer/5/  or  /payments/add/supplier/3/
    path('add/<slug:content_type_slug>/<int:object_id>/', views.PaymentCreateView.as_view(),name='payment_create',
    ),
]