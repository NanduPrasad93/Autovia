from django import forms
from django.core.exceptions import ValidationError
from .models import Vehicle
import datetime


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            'registration_number',
            'manufacturer',
            'model_name',
            'manufacturing_year',
            'fuel_type',
            'color',
            'chassis_number',
            'current_odometer',
        ]
        widgets = {
            'registration_number': forms.TextInput(attrs={
                'class': 'form-control text-uppercase font-monospace',
                'placeholder': 'e.g. KA-01-AB-1234',
                'required': True,
            }),
            'manufacturer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Toyota, Honda, BMW',
                'required': True,
            }),
            'model_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Camry, Civic, M340i',
                'required': True,
            }),
            'manufacturing_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 2022',
                'min': 1950,
                'max': datetime.date.today().year + 1,
                'required': True,
            }),
            'fuel_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Alpine White, Metallic Blue',
                'required': True,
            }),
            'chassis_number': forms.TextInput(attrs={
                'class': 'form-control font-monospace',
                'placeholder': 'Optional 17-digit VIN / chassis number',
            }),
            'current_odometer': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Current mileage in km',
                'min': 0,
                'required': True,
            }),
        }

    def clean_registration_number(self):
        reg_no = self.cleaned_data.get('registration_number', '').strip().upper()
        # Query excluding current instance if editing
        qs = Vehicle.objects.filter(registration_number__iexact=reg_no)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A vehicle with this registration number already exists in the system.")
        return reg_no

    def clean_manufacturing_year(self):
        year = self.cleaned_data.get('manufacturing_year')
        current_year = datetime.date.today().year
        if year and (year < 1900 or year > current_year + 1):
            raise ValidationError(f"Please provide a realistic manufacturing year (1900 - {current_year + 1}).")
        return year
