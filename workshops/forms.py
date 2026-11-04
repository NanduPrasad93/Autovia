from django import forms
from decimal import Decimal
from .models import Workshop
from services.models import RepairEstimate, RepairBill


class WorkshopProfileForm(forms.ModelForm):
    """Form for workshop owners to update their workshop facility details."""

    class Meta:
        model = Workshop
        fields = [
            'workshop_name',
            'description',
            'address',
            'phone_number',
            'services_offered',
            'workshop_image',
        ]
        widgets = {
            'workshop_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Apex Auto Care & Performance Centre',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Provide an overview of your workshop capabilities, facility equipment, and bays...',
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Full street address, district, state/province, postal code',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 (555) 019-2834',
            }),
            'services_offered': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'e.g. Engine Overhauls, Transmission Diagnostics, Body & Paint, Wheel Alignment, AC Servicing',
            }),
            'workshop_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if not phone:
            raise forms.ValidationError("Contact phone number is required.")
        return phone


class WorkshopRepairEstimateForm(forms.ModelForm):
    """Form for workshops to prepare or edit formal itemized repair quotations."""

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
                'class': 'form-control estimate-calc',
                'step': '0.01',
                'min': '0',
                'id': 'id_labor_cost',
            }),
            'parts_cost': forms.NumberInput(attrs={
                'class': 'form-control estimate-calc',
                'step': '0.01',
                'min': '0',
                'id': 'id_parts_cost',
            }),
            'additional_cost': forms.NumberInput(attrs={
                'class': 'form-control estimate-calc',
                'step': '0.01',
                'min': '0',
                'id': 'id_additional_cost',
            }),
            'estimated_completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Itemize parts needed, diagnostics performed, and estimated labor breakdown...',
            }),
        }

    def clean_labor_cost(self):
        val = self.cleaned_data.get('labor_cost')
        if val is not None and val < Decimal('0.00'):
            raise forms.ValidationError("Labor cost cannot be negative.")
        return val or Decimal('0.00')

    def clean_parts_cost(self):
        val = self.cleaned_data.get('parts_cost')
        if val is not None and val < Decimal('0.00'):
            raise forms.ValidationError("Parts cost cannot be negative.")
        return val or Decimal('0.00')

    def clean_additional_cost(self):
        val = self.cleaned_data.get('additional_cost')
        if val is not None and val < Decimal('0.00'):
            raise forms.ValidationError("Additional cost cannot be negative.")
        return val or Decimal('0.00')


class WorkshopRepairBillForm(forms.ModelForm):
    """Form for workshops to generate final itemized repair bills."""

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
                'placeholder': 'Comprehensive summary of all completed mechanical procedures, replacements, and testing...',
            }),
            'labor_charges': forms.NumberInput(attrs={
                'class': 'form-control bill-calc',
                'step': '0.01',
                'min': '0',
                'id': 'id_labor_charges',
            }),
            'parts_charges': forms.NumberInput(attrs={
                'class': 'form-control bill-calc',
                'step': '0.01',
                'min': '0',
                'id': 'id_parts_charges',
            }),
            'additional_charges': forms.NumberInput(attrs={
                'class': 'form-control bill-calc',
                'step': '0.01',
                'min': '0',
                'id': 'id_additional_charges',
            }),
            'service_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select',
            }),
            'is_paid': forms.CheckboxInput(attrs={
                'class': 'form-check-input ms-1',
            }),
        }

    def clean_labor_charges(self):
        val = self.cleaned_data.get('labor_charges')
        if val is not None and val < Decimal('0.00'):
            raise forms.ValidationError("Labor charges cannot be negative.")
        return val or Decimal('0.00')

    def clean_parts_charges(self):
        val = self.cleaned_data.get('parts_charges')
        if val is not None and val < Decimal('0.00'):
            raise forms.ValidationError("Parts charges cannot be negative.")
        return val or Decimal('0.00')

    def clean_additional_charges(self):
        val = self.cleaned_data.get('additional_charges')
        if val is not None and val < Decimal('0.00'):
            raise forms.ValidationError("Additional charges cannot be negative.")
        return val or Decimal('0.00')
