"""
MediPOS Reports — URL Configuration.

URL patterns for all report views.
"""
from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.ReportDashboardView.as_view(), name='report_dashboard'),
    path('sales/', views.SalesSummaryView.as_view(), name='sales_summary'),
    path('profit-loss/', views.ProfitLossView.as_view(), name='profit_loss'),
    path('product-sales/', views.ProductSalesView.as_view(), name='product_sales'),
    path('stock-valuation/', views.StockValuationView.as_view(), name='stock_valuation'),
    path('expiry/', views.ExpiryReportView.as_view(), name='expiry_report'),
    path('top-selling/', views.TopSellingView.as_view(), name='top_selling'),
]