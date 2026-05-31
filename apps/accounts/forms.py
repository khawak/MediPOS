"""
MediPOS Accounts — Forms.

Defines all forms for authentication, user management, and profile editing
with Bootstrap 5 rendering via django-crispy-forms.
"""

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm as DjangoPasswordChangeForm,
    UserCreationForm,
)
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Field

from .models import User


class LoginForm(AuthenticationForm):
    """
    Custom login form with Bootstrap 5 styling via crispy-forms.

    Extends Django's AuthenticationForm to provide a centered, branded
    login experience for MediPOS.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the form with crispy-forms layout for Bootstrap 5."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        self.helper.layout = Layout(
            Field('username', placeholder='Enter your username'),
            Field('password', placeholder='Enter your password'),
            Submit('submit', 'Sign In', css_class='btn btn-primary w-100'),
        )


class UserCreateForm(UserCreationForm):
    """
    Form for creating new users (admin-only).

    Extends UserCreationForm to include the role, phone, and avatar fields
    required by the MediPOS system.
    """

    class Meta(UserCreationForm.Meta):
        """Metadata for the UserCreateForm."""

        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'phone',
            'role',
            'password1',
            'password2',
        )

    def __init__(self, *args, **kwargs):
        """Initialize the form with crispy-forms layout."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        self.helper.layout = Layout(
            Row(
                Column(Field('username'), css_class='col-md-6'),
                Column(Field('email'), css_class='col-md-6'),
            ),
            Row(
                Column(Field('first_name'), css_class='col-md-6'),
                Column(Field('last_name'), css_class='col-md-6'),
            ),
            Row(
                Column(Field('phone'), css_class='col-md-6'),
                Column(Field('role'), css_class='col-md-6'),
            ),
            Field('password1'),
            Field('password2'),
            Submit('submit', 'Create User', css_class='btn btn-primary'),
        )


class UserEditForm(forms.ModelForm):
    """
    Form for editing user details (admin-only).

    Allows administrators to modify user information including role
    assignment and active status.
    """

    class Meta:
        """Metadata for the UserEditForm."""

        model = User
        fields = (
            'first_name',
            'last_name',
            'email',
            'phone',
            'role',
            'is_active',
        )

    def __init__(self, *args, **kwargs):
        """Initialize the form with crispy-forms layout."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        self.helper.layout = Layout(
            Row(
                Column(Field('first_name'), css_class='col-md-6'),
                Column(Field('last_name'), css_class='col-md-6'),
            ),
            Row(
                Column(Field('email'), css_class='col-md-6'),
                Column(Field('phone'), css_class='col-md-6'),
            ),
            Row(
                Column(Field('role'), css_class='col-md-6'),
                Column(Field('is_active'), css_class='col-md-6'),
            ),
            Submit('submit', 'Save Changes', css_class='btn btn-primary'),
        )


class ProfileUpdateForm(forms.ModelForm):
    """
    Form for logged-in users to update their own profile.

    Allows users to edit their name, email, phone, and avatar.
    Role and active status are excluded for security.
    """

    class Meta:
        """Metadata for the ProfileUpdateForm."""

        model = User
        fields = (
            'first_name',
            'last_name',
            'email',
            'phone',
            'avatar',
        )

    def __init__(self, *args, **kwargs):
        """Initialize the form with crispy-forms layout."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_attrs = {'enctype': 'multipart/form-data'}
        self.helper.form_class = 'needs-validation'
        self.helper.layout = Layout(
            Row(
                Column(Field('first_name'), css_class='col-md-6'),
                Column(Field('last_name'), css_class='col-md-6'),
            ),
            Row(
                Column(Field('email'), css_class='col-md-6'),
                Column(Field('phone'), css_class='col-md-6'),
            ),
            Field('avatar'),
            Submit('submit', 'Update Profile', css_class='btn btn-primary'),
        )


class PasswordChangeForm(DjangoPasswordChangeForm):
    """
    Custom password change form with Bootstrap 5 styling.

    Extends Django's PasswordChangeForm to use crispy-forms rendering.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the form with crispy-forms layout."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        self.helper.layout = Layout(
            Field('old_password', placeholder='Enter current password'),
            Field('new_password1', placeholder='Enter new password'),
            Field('new_password2', placeholder='Confirm new password'),
            Submit(
                'submit',
                'Change Password',
                css_class='btn btn-primary',
            ),
        )