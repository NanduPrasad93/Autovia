from django import forms
from decimal import Decimal
from .models import SupplierProfile, SparePart


class SupplierProfileForm(forms.ModelForm):
    """Form for spare parts suppliers to manage business credentials and contact details."""
    contact_email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'orders@supplier.com',
        }),
        help_text="Official email address for purchase orders and delivery dispatch notices."
    )

    class Meta:
        model = SupplierProfile
        fields = [
            'business_name',
            'business_address',
            'phone_number',
            'description',
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Apex OEM Auto Parts & Wholesale Distribution',
            }),
            'business_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Warehouse & Distribution facility address, city, state, postal code',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 (555) 019-4829',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your catalog specializations, OEM partnerships, warranty coverage, and distribution regions...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            self.fields['contact_email'].initial = self.instance.user.email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if not phone:
            raise forms.ValidationError("Operational contact phone number is required.")
        return phone


class SparePartForm(forms.ModelForm):
    """Form for suppliers to add and edit catalog spare parts."""

    class Meta:
        model = SparePart
        fields = [
            'part_name',
            'part_number',
            'compatible_manufacturer',
            'compatible_vehicle_models',
            'price',
            'stock_quantity',
            'image',
            'is_available',
            'description',
        ]
        widgets = {
            'part_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Ceramic Front Brake Pad Set',
            }),
            'part_number': forms.TextInput(attrs={
                'class': 'form-control font-monospace',
                'placeholder': 'e.g. BP-TY-2023-FR',
            }),
            'compatible_manufacturer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Toyota, Honda, Ford (or Multi-Manufacturer)',
            }),
            'compatible_vehicle_models': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'e.g. RAV4 (2019-2024), Camry (2018-2023), Corolla Cross',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00',
            }),
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': '0',
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Technical specifications, material composition, warranty period, and installation notes...',
            }),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None or price <= Decimal('0.00'):
            raise forms.ValidationError("Product price must be greater than zero.")
        return price

    def clean_stock_quantity(self):
        qty = self.cleaned_data.get('stock_quantity')
        if qty is None or qty < 0:
            raise forms.ValidationError("Available stock quantity cannot be negative.")
        return qty

    def clean_part_number(self):
        part_number = self.cleaned_data.get('part_number', '').strip().upper()
        if not part_number:
            raise forms.ValidationError("Part / SKU number is required.")

        qs = SparePart.objects.filter(part_number__iexact=part_number)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(f"A product with Part Number '{part_number}' is already registered in the catalog.")
        return part_number
