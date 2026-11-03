from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import UserProfile


PUBLIC_ROLES = [
    (UserProfile.Role.VEHICLE_OWNER, 'Vehicle Owner (Driver / Car Owner)'),
    (UserProfile.Role.MECHANIC, 'Professional Mechanic (Freelance / Mobile)'),
    (UserProfile.Role.WORKSHOP, 'Workshop / Service Centre (Garage Owner)'),
    (UserProfile.Role.SUPPLIER, 'Spare Parts Supplier / Retailer'),
]


class LoginForm(forms.Form):
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username or email',
            'autocomplete': 'username',
            'required': True,
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
            'autocomplete': 'current-password',
            'required': True,
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        label="Remember me for 30 days",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )


class RegistrationForm(forms.Form):
    full_name = forms.CharField(
        label="Full Name",
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. John Doe',
            'required': True,
        })
    )
    username = forms.CharField(
        label="Username",
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a unique username',
            'autocomplete': 'username',
            'required': True,
        })
    )
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'name@example.com',
            'autocomplete': 'email',
            'required': True,
        })
    )
    phone_number = forms.CharField(
        label="Phone Number",
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1 (555) 000-0000',
            'required': True,
        })
    )
    account_type = forms.ChoiceField(
        label="Account Type",
        choices=PUBLIC_ROLES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True,
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create strong password',
            'autocomplete': 'new-password',
            'required': True,
        })
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat your password',
            'autocomplete': 'new-password',
            'required': True,
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken. Please choose another one.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_account_type(self):
        account_type = self.cleaned_data.get('account_type')
        valid_roles = [r[0] for r in PUBLIC_ROLES]
        if account_type == UserProfile.Role.ADMIN or account_type not in valid_roles:
            raise ValidationError("Invalid account type. Public registration as Administrator is strictly prohibited.")
        return account_type

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                self.add_error('confirm_password', "Passwords do not match.")
            else:
                # Validate password strength using Django validators
                try:
                    validate_password(password)
                except ValidationError as e:
                    self.add_error('password', e)

        return cleaned_data
