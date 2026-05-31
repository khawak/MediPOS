"""
MediPOS Sales — URL Configuration.

Defines all URL patterns for the point-of-sale billing interface,
cart API endpoints, invoice display, and sale history views.

App name: sales
"""
from django.urls import path

from . import views

app_name = 'sales'

urlpatterns = [
    # Sale history list
    path('', views.SaleListView.as_view(), name='sale_list'),

    # POS main screen
    path('pos/', views.POSView.as_view(), name='pos'),

    # Cart API endpoints
    path('pos/cart/', views.CartGetView.as_view(), name='cart_get'),
    path('pos/cart/add/', views.CartAddItemView.as_view(), name='cart_add'),
    path('pos/cart/remove/', views.CartRemoveItemView.as_view(), name='cart_remove'),
    path('pos/cart/update/', views.CartUpdateQuantityView.as_view(), name='cart_update'),
    path('pos/cart/discount/', views.CartUpdateDiscountView.as_view(), name='cart_discount'),
    path('pos/cart/customer/', views.CartSetCustomerView.as_view(), name='cart_customer'),
    path('pos/medicine-search/', views.MedicineSearchView.as_view(), name='medicine_search'),

    # Checkout
    path('pos/checkout/', views.CheckoutView.as_view(), name='checkout'),

    # Hold / Resume
    path('pos/hold/', views.HoldSaleView.as_view(), name='hold_sale'),
    path('pos/resume/<int:sale_id>/', views.ResumeSaleView.as_view(), name='resume_sale'),

    # Sale detail & invoices
    path('<int:pk>/', views.SaleDetailView.as_view(), name='sale_detail'),
    path('<int:pk>/invoice/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('<int:pk>/invoice/print/', views.InvoicePrintView.as_view(), name='invoice_print'),
    path('<int:pk>/invoice/thermal/', views.InvoiceThermalPrintView.as_view(), name='invoice_thermal'),

    # Cancel sale
    path('<int:pk>/cancel/', views.CancelSaleView.as_view(), name='cancel_sale'),
]