"""
MediPOS Medicines — URL Configuration.

Defines URL patterns for Category and Medicine management.
"""
from django.urls import path

from . import views

app_name = 'medicines'

urlpatterns = [
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