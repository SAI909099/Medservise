from datetime import timedelta
import random
from django.db import models

from django.db import models
from django.db.models import CharField, Model, ForeignKey, IntegerField, DateTimeField, CASCADE, OneToOneField, \
    DecimalField
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
    user = OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Service(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    doctor = models.ForeignKey('Doctor', on_delete=CASCADE, related_name='services')

    def __str__(self):
        return f"{self.name} (${self.price}) - {self.doctor.name}"


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
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    result_file = models.FileField(upload_to="uploads/results/" , null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)





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





class TreatmentRoom(models.Model):
    name = models.CharField(max_length=100)  # e.g. '1-room', '2-room'
    capacity = models.PositiveIntegerField(default=1)
    floor = models.IntegerField(default=1)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.name} (for {self.capacity} patients)"

class TreatmentRegistration(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    room = models.ForeignKey(TreatmentRoom, on_delete=models.SET_NULL, null=True)
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True)  # ✅ Add this
    assigned_at = models.DateTimeField(auto_now_add=True)
    discharged_at = models.DateTimeField(null=True, blank=True)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def is_active(self):
        return self.discharged_at is None


# class TreatmentRegistration(models.Model):
#     patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
#     room = models.ForeignKey(TreatmentRoom, on_delete=models.SET_NULL, null=True)
#     registered_at = models.DateTimeField(auto_now_add=True)
#     discharged_at = models.DateTimeField(null=True, blank=True)
#     total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
#
#     def is_active(self):
#         return self.discharged_at is None



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

class Payment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, blank=True)
    consultation_paid = models.BooleanField(default=False)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    debt = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)




