"""
MediPOS Medicines — URL Configuration.

Defines URL patterns for Category and Medicine management.
"""
from django.urls import path

from . import views

app_name = 'medicines'

urlpatterns = [
    # ── Generic Name URLs ───────────────────────────────────────────────────
    path(
        'generic-names/',
        views.GenericNameListView.as_view(),
        name='generic_name_list',
    ),
    path(
        'generic-names/add/',
        views.GenericNameCreateView.as_view(),
        name='generic_name_add',
    ),
    path(
        'generic-names/<int:pk>/edit/',
        views.GenericNameUpdateView.as_view(),
        name='generic_name_edit',
    ),
    path(
        'generic-names/<int:pk>/delete/',
        views.GenericNameDeleteView.as_view(),
        name='generic_name_delete',
    ),

    # ── Category URLs ───────────────────────────────────────────────────────
    path(
        'categories/',
        views.CategoryListView.as_view(),
        name='category_list',
    ),
    path(
        'categories/add/',
        views.CategoryCreateView.as_view(),
        name='category_add',
    ),
    path(
        'categories/<slug:slug>/edit/',
        views.CategoryUpdateView.as_view(),
        name='category_edit',
    ),
    path(
        'categories/<slug:slug>/delete/',
        views.CategoryDeleteView.as_view(),
        name='category_delete',
    ),
    path(
        'categories/import/',
        views.CategoryBulkImportView.as_view(),
        name='category_import',
    ),
    path(
        'categories/template/download/',
        views.download_category_import_template,
        name='download_category_template',
    ),

    # ── AJAX Search ─────────────────────────────────────────────────────────────
    path(
        'search/generic-names/',
        views.GenericNameSearchView.as_view(),
        name='generic_name_search',
    ),
    path(
        'search/categories/',
        views.CategorySearchView.as_view(),
        name='category_search',
    ),
    path(
        'search/brands/',
        views.BrandSearchView.as_view(),
        name='brand_search',
    ),
    path(
        'search/by-category/',
        views.MedicinesByCategoryView.as_view(),
        name='medicines_by_category',
    ),
    path(
        'search/medicines/',
        views.MedicineSearchView.as_view(),
        name='medicine_search',
    ),

    # ── Medicine URLs ───────────────────────────────────────────────────────
    path(
        '',
        views.MedicineListView.as_view(),
        name='medicine_list',
    ),
    path(
        'add/',
        views.MedicineCreateView.as_view(),
        name='medicine_add',
    ),
    path(
        '<int:pk>/',
        views.MedicineDetailView.as_view(),
        name='medicine_detail',
    ),
    path(
        '<int:pk>/edit/',
        views.MedicineUpdateView.as_view(),
        name='medicine_edit',
    ),
    path(
        '<int:pk>/delete/',
        views.MedicineDeleteView.as_view(),
        name='medicine_delete',
    ),

    # ── Bulk Import ─────────────────────────────────────────────────────────
    path(
        'import/',
        views.MedicineBulkImportView.as_view(),
        name='medicine_import',
    ),
    path(
        'template/download/',
        views.download_import_template,
        name='download_template',
    ),
]