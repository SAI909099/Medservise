import random
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import DateField, CharField, EmailField, BooleanField
from django.db.models import Model, ForeignKey, DateTimeField, CASCADE, OneToOneField
from django.utils import timezone
from django.utils.timezone import now
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.manager import CustomUserManager
from django.conf import settings
from django.utils.translation import gettext_lazy as _

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
    is_cashier = BooleanField(default=False)
    is_accountant = BooleanField(default=False)
    is_registrator = BooleanField(default=False)


    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = CustomUserManager()


class Doctor(models.Model):
    user = OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100)
    consultation_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

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
    services = models.ManyToManyField(Service, blank=True, related_name='patients')
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
    reason = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    services = models.ManyToManyField('Service', blank=True)
    turn_number = models.CharField(max_length=10, null=True, blank=True)
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
    assigned_at = models.DateTimeField(default=timezone.now)
    discharged_at = models.DateTimeField(null=True, blank=True)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def is_active(self):
        return self.discharged_at is None


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
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="payment")
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('paid', 'Paid'), ('unpaid', 'Unpaid')])
    created_at = models.DateTimeField(auto_now_add=True)
    repeat_count = models.PositiveIntegerField(default=0)


class TreatmentPayment(models.Model):
    patient = models.ForeignKey("Patient", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('paid', 'Paid'), ('partial', 'Partial'), ('unpaid', 'Unpaid')])
    notes = models.TextField(blank=True)
    payment_method = models.CharField(max_length=20)
    date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class CashRegister(models.Model):
    TRANSACTION_TYPES = [
        ('consultation', _('Konsultatsiya')),
        ('treatment', _('Davolash')),
        ('service', _('Xizmat')),
        ('room', _('Xona to‘lovi')),
        ('other', _('Boshqa')),
    ]

    PAYMENT_METHODS = [
        ('cash', _('Naqd')),
        ('card', _('Karta')),
        ('insurance', _('Sug‘urta')),
        ('transfer', _('Bank o‘tkazmasi')),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    turn_number = models.CharField(max_length=10, blank=True, null=True)
    doctor = models.ForeignKey('Doctor', on_delete=models.SET_NULL, null=True, blank=True)
    room = models.ForeignKey("TreatmentRoom", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.patient} - {self.get_transaction_type_display()} - {self.amount}"


class TurnNumber(models.Model):
    doctor = models.OneToOneField(Doctor, on_delete=models.CASCADE)
    letter = models.CharField(max_length=1)  # A, B, C, etc.
    current_number = models.IntegerField(default=0)
    last_reset = models.DateField(auto_now_add=True)

    def get_next_turn(self):
        today = timezone.now().date()
        if self.last_reset != today:
            self.current_number = 1
            self.last_reset = today
        else:
            self.current_number += 1
        self.save()
        return f"{self.letter}{self.current_number:03d}"


class CallTurnView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        appointment_id = request.data.get("appointment_id")
        if not appointment_id:
            return Response({"error": "appointment_id required"}, status=400)

        try:
            appointment = Appointment.objects.select_related("patient", "doctor").get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response({"error": "Appointment not found"}, status=404)

        # Save or update last-called time for frontend highlighting (optional)
        appointment.last_called = now()
        appointment.save()

        # You can log or broadcast this action (via Redis/Channel/Socket later if needed)
        return Response({"message": "Patient called"}, status=200)

class CurrentCall(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE)
    called_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.appointment.patient} → {self.appointment.doctor}"





class Outcome(models.Model):
    CATEGORY_CHOICES = [
        ('salary', "Maosh"),
        ('equipment', "Jihozlar"),
        ('rent', "Ijaralar"),
        ('supplies', "Materiallar"),
        ('other', "Boshqa"),
    ]

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('cash', 'Naqd'),
            ('card', 'Karta'),
            ('transfer', 'O‘tkazma'),
        ]
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.amount} so'm"



class LabRegistration(models.Model):
    STATUS_CHOICES = [
        ("pending", "Kutilmoqda"),
        ("completed", "Bajarilgan"),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    visit = models.ForeignKey(TreatmentRegistration, on_delete=models.CASCADE, null=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    repeat_count = models.PositiveIntegerField(default=0)


class Visit(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='visits')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='visits')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Visit: {self.patient} to {self.doctor} on {self.created_at}"
