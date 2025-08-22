
from django import forms
from .models import Patient, Appointment, Doctor

class PatientRegistrationForm(forms.ModelForm):
    reason = forms.CharField(widget=forms.Textarea, label="Reason for visit")
    doctor = forms.ModelChoiceField(queryset=Doctor.objects.all(), label="Select Doctor")

    class Meta:
        model = Patient
        fields = ['first_name', 'last_name', 'phone', 'address']
