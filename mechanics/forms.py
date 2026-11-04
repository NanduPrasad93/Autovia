from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
import datetime
from .models import MechanicProfile
from services.models import RepairEstimate, RepairBill


class MechanicProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        label="First Name",
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'required': True})
    )
    last_name = forms.CharField(
        label="Last Name",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        label="Phone Number",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 (555) 000-0000'})
    )
    profile_image = forms.ImageField(
        label="Profile Image",
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = MechanicProfile
        fields = [
            'specialization',
            'experience_years',
            'service_location',
            'description',
        ]
        widgets = {
            'specialization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Engine Diagnostics, Brake Systems, Auto Electrical',
                'required': True,
            }),
            'experience_years': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '60',
                'required': True,
            }),
            'service_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Downtown Metro, South District, Mobile Service',
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detail your automotive certifications, brand specializations, and workshop facilities...',
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            if hasattr(user, 'profile'):
                self.fields['phone_number'].initial = user.profile.phone_number
                if user.profile.profile_image:
                    self.fields['profile_image'].initial = user.profile.profile_image

    def clean_experience_years(self):
        exp = self.cleaned_data.get('experience_years')
        if exp is not None and exp < 0:
            raise ValidationError("Experience years cannot be negative.")
        return exp


class RepairEstimateForm(forms.ModelForm):
    class Meta:
        model = RepairEstimate
        fields = [
            'labor_cost',
            'parts_cost',
            'additional_cost',
            'estimated_completion_date',
            'description',
        ]
        widgets = {
            'labor_cost': forms.NumberInput(attrs={
                'class': 'form-control cost-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
            'parts_cost': forms.NumberInput(attrs={
                'class': 'form-control cost-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
            'additional_cost': forms.NumberInput(attrs={
                'class': 'form-control cost-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
            'estimated_completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Provide an itemized breakdown of expected labor, replacement parts required, and diagnosis notes...',
                'required': True,
            }),
        }

    def clean_labor_cost(self):
        val = self.cleaned_data.get('labor_cost')
        if val is not None and val < Decimal('0.00'):
            raise ValidationError("Labor cost cannot be negative.")
        return val or Decimal('0.00')

    def clean_parts_cost(self):
        val = self.cleaned_data.get('parts_cost')
        if val is not None and val < Decimal('0.00'):
            raise ValidationError("Parts cost cannot be negative.")
        return val or Decimal('0.00')

    def clean_additional_cost(self):
        val = self.cleaned_data.get('additional_cost')
        if val is not None and val < Decimal('0.00'):
            raise ValidationError("Additional cost cannot be negative.")
        return val or Decimal('0.00')

    def clean_estimated_completion_date(self):
        dt = self.cleaned_data.get('estimated_completion_date')
        if dt and dt < datetime.date.today():
            raise ValidationError("Estimated completion date cannot be in the past.")
        return dt


class RepairBillForm(forms.ModelForm):
    class Meta:
        model = RepairBill
        fields = [
            'service_description',
            'labor_charges',
            'parts_charges',
            'additional_charges',
            'service_date',
            'payment_method',
            'is_paid',
        ]
        widgets = {
            'service_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detail all executed repair operations, parts installed, diagnostics completed, and warranty advice...',
                'required': True,
            }),
            'labor_charges': forms.NumberInput(attrs={
                'class': 'form-control bill-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
            'parts_charges': forms.NumberInput(attrs={
                'class': 'form-control bill-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
            'additional_charges': forms.NumberInput(attrs={
                'class': 'form-control bill-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
            'service_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select',
            }),
            'is_paid': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_labor_charges(self):
        val = self.cleaned_data.get('labor_charges')
        if val is not None and val < Decimal('0.00'):
            raise ValidationError("Labor charges cannot be negative.")
        return val or Decimal('0.00')

    def clean_parts_charges(self):
        val = self.cleaned_data.get('parts_charges')
        if val is not None and val < Decimal('0.00'):
            raise ValidationError("Parts charges cannot be negative.")
        return val or Decimal('0.00')

    def clean_additional_charges(self):
        val = self.cleaned_data.get('additional_charges')
        if val is not None and val < Decimal('0.00'):
            raise ValidationError("Additional charges cannot be negative.")
        return val or Decimal('0.00')
