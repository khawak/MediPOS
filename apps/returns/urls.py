"""
MediPOS Returns & Refunds — URL Configuration.

URL patterns for the sales returns & refunds app.
"""
from django.urls import path

from . import views

app_name = 'returns'

urlpatterns = [
    # List all sales returns
    path('', views.SalesReturnListView.as_view(), name='sales_return_list'),

    # Create a new sales return
    path('create/', views.SalesReturnCreateView.as_view(), name='sales_return_create'),

    # View return details
    path('<int:pk>/', views.SalesReturnDetailView.as_view(), name='sales_return_detail'),
]