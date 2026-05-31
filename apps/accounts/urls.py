"""
MediPOS Accounts URL Configuration.

Route definitions for authentication, user management, and profile pages.
"""

from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    # ── Authentication ──────────────────────────────────────────────────
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # ── Password Management ─────────────────────────────────────────────
    path(
        'password-change/',
        views.PasswordChangeView.as_view(),
        name='password_change',
    ),
    path(
        'password-change/done/',
        views.PasswordChangeDoneView.as_view(),
        name='password_change_done',
    ),

    # ── User Management (Admin Only) ────────────────────────────────────
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/add/', views.UserCreateView.as_view(), name='user_add'),
    path(
        'users/<int:pk>/',
        views.UserDetailView.as_view(),
        name='user_detail',
    ),
    path(
        'users/<int:pk>/edit/',
        views.UserUpdateView.as_view(),
        name='user_edit',
    ),
    path(
        'users/<int:pk>/delete/',
        views.UserDeleteView.as_view(),
        name='user_delete',
    ),

    # ── Profile (Authenticated Users) ───────────────────────────────────
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path(
        'profile/edit/',
        views.ProfileUpdateView.as_view(),
        name='profile_edit',
    ),
]