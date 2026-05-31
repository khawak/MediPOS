"""
MediPOS Settings — URL Configuration.
"""
from django.urls import path

from . import views

app_name = 'settings'

urlpatterns = [
    path('', views.SettingsUpdateView.as_view(), name='settings_update'),
    path('backup/', views.BackupDatabaseView.as_view(), name='backup'),
]