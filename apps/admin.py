from django.contrib import admin
from django import forms
from .models import Patient, Doctor, Appointment, Payment, TreatmentRoom, TreatmentRegistration

# ---------------- PatientAdmin with doctor selection ---------------- #

class PatientAdminForm(forms.ModelForm):
    doctor = forms.ModelChoiceField(
        queryset=Doctor.objects.all(),
        required=False,
        label="Assign Doctor (auto-create appointment)"
    )

    class Meta:
        model = Patient
        fields = '__all__'

class PatientAdmin(admin.ModelAdmin):
    form = PatientAdminForm

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        doctor = form.cleaned_data.get('doctor')
        if doctor:
            Appointment.objects.create(
                patient=obj,
                doctor=doctor,
                reason="Admin registration",
                status="queued"
            )

# ---------------- DoctorAdmin with appointment inline ---------------- #

class AppointmentInline(admin.TabularInline):
    model = Appointment
    fk_name = 'doctor'
    extra = 0
    fields = ('patient', 'reason', 'status', 'created_at')
    readonly_fields = ('patient', 'reason', 'status', 'created_at')
    can_delete = False
    show_change_link = True

class DoctorAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialty', 'queued_patients_count')
    inlines = [AppointmentInline]

    def queued_patients_count(self, obj):
        return obj.appointments.filter(status="queued").count()
    queued_patients_count.short_description = "Patients Waiting"

# ---------------- Register all models ---------------- #

admin.site.register(Patient, PatientAdmin)
admin.site.register(Doctor, DoctorAdmin)
admin.site.register(Appointment)
admin.site.register(Payment)
admin.site.register(TreatmentRoom)
admin.site.register(TreatmentRegistration)
