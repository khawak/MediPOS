"""
MediPOS Customers — URL Configuration.

Defines URL patterns for Customer management.
"""
from django.urls import path

from . import views

app_name = 'customers'

urlpatterns = [
    path(
        '',
        views.CustomerListView.as_view(),
        name='customer_list',
    ),
    path(
        'add/',
        views.CustomerCreateView.as_view(),
        name='customer_add',
    ),
    path(
        'quick-add/',
        views.CustomerQuickCreateView.as_view(),
        name='customer_quick_add',
    ),
    path(
        '<int:pk>/',
        views.CustomerDetailView.as_view(),
        name='customer_detail',
    ),
    path(
        '<int:pk>/edit/',
        views.CustomerUpdateView.as_view(),
        name='customer_edit',
    ),
    path(
        '<int:pk>/delete/',
        views.CustomerDeleteView.as_view(),
        name='customer_delete',
    ),
]