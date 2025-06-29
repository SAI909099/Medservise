from datetime import timedelta
import random
from django.db import models

from django.db import models
from django.db.models import CharField, Model, ForeignKey, IntegerField, DateTimeField, CASCADE, OneToOneField
from django.utils.timezone import now

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import DateField, CharField, EmailField, BooleanField

from apps.manager import CustomUserManager



class User(AbstractUser):
    username = None
    first_name = CharField(max_length=50)
    last_name = CharField(max_length=50)
    date_of_birth = DateField(null=True, blank=True)
    phone_number = CharField(max_length=15, null=True, blank=True)
    email = EmailField(unique=True)
    is_active = BooleanField(default=False)
    reset_token = CharField(max_length=64, null=True, blank=True)
    is_doctor = BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = CustomUserManager()



class Doctor(models.Model):
    user = OneToOneField(User, on_delete=models.CASCADE , blank=True, null=True)
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100)

    def __str__(self):
        return self.name



class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    patients_doctor = ForeignKey(Doctor, on_delete=CASCADE, null=True , blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class PatientResult(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='results')
    title = models.CharField(max_length=255)  # e.g., "Blood Test", "MRI"
    file = models.FileField(upload_to='patient_results/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} for {self.patient}"




class Appointment(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('assigned', 'Assigned'),
        ('cancelled', 'Cancelled'),
        ('done', 'Done')
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    referred_by = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_appointments')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient} with {self.doctor}"


class Payment(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"${self.amount_paid} for {self.appointment}"


class TreatmentRoom(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.IntegerField(default=1)
    is_busy = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class TreatmentRegistration(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    treatment_room = models.ForeignKey(TreatmentRoom, on_delete=models.CASCADE)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.appointment.patient} in {self.treatment_room}"

    def total_paid(self):
        return sum(p.amount_paid for p in Payment.objects.filter(appointment=self.appointment))

    def amount_due(self):
        return max(0, self.payment_amount - self.total_paid())



#     -/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-///-/--/-//-/-/-//--//-/-/-/-/--//-/-/-/-/-/-/-/-



class VerificationCode(Model):
    email = EmailField(unique=True)
    code = CharField(max_length=6)
    created_at = DateTimeField(auto_now_add=True)

    def is_expired(self):
        return now() > self.created_at + timedelta(minutes=10)

    @staticmethod
    def generate_code():
        return str(random.randint(100000, 999999))
