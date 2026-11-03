from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import ServiceRequest
from vehicles.models import Vehicle
from mechanics.models import MechanicProfile
from workshops.models import Workshop


class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = [
            'vehicle',
            'problem_description',
            'mechanic',
            'workshop',
            'requested_date',
        ]
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'problem_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the automobile issue, symptoms, strange noises, warning lights, or requested maintenance in detail...',
                'required': True,
            }),
            'mechanic': forms.Select(attrs={'class': 'form-select'}),
            'workshop': forms.Select(attrs={'class': 'form-select'}),
            'requested_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': True,
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['vehicle'].queryset = Vehicle.objects.filter(owner=user)

        self.fields['mechanic'].queryset = MechanicProfile.objects.all()
        self.fields['mechanic'].required = False
        self.fields['mechanic'].empty_label = "-- Select an Individual Mechanic (Optional) --"

        self.fields['workshop'].queryset = Workshop.objects.all()
        self.fields['workshop'].required = False
        self.fields['workshop'].empty_label = "-- Select a Certified Workshop (Optional) --"

    def clean(self):
        cleaned_data = super().clean()
        mechanic = cleaned_data.get('mechanic')
        workshop = cleaned_data.get('workshop')
        requested_date = cleaned_data.get('requested_date')

        if mechanic and workshop:
            raise ValidationError("Please assign the request to either an individual mechanic OR a workshop, not both.")

        if requested_date and requested_date < timezone.now() - timezone.timedelta(minutes=30):
            raise ValidationError("Requested service appointment date cannot be in the past.")

        return cleaned_data
