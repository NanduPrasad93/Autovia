from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Expense
from vehicles.models import Vehicle


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            'vehicle',
            'category',
            'amount',
            'description',
            'expense_date',
        ]
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'category': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00',
                'required': True,
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 45L Premium Petrol fill-up, Shell Station',
            }),
            'expense_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['vehicle'].queryset = Vehicle.objects.filter(owner=self.user)
        self.fields['expense_date'].initial = timezone.now().date()

    def clean_vehicle(self):
        vehicle = self.cleaned_data.get('vehicle')
        if vehicle and self.user and vehicle.owner != self.user:
            raise ValidationError("You may only record expenses for vehicles registered in your garage.")
        return vehicle

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise ValidationError("Expense amount must be greater than zero.")
        return amount

    def clean_expense_date(self):
        expense_date = self.cleaned_data.get('expense_date')
        if expense_date and expense_date > timezone.now().date():
            raise ValidationError("Expense date cannot be set in the future.")
        return expense_date
