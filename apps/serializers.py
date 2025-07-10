from datetime import timedelta
from urllib.parse import urlparse

import redis
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import ValidationError
from django.db.models import OneToOneField, CASCADE, ForeignKey
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import HiddenField, CurrentUserDefault, IntegerField
from rest_framework.serializers import ModelSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from root import settings
from .models import User, Doctor, Patient, PatientResult, Service, TreatmentPayment, CashRegister, TurnNumber, Outcome

redis_url = urlparse(settings.CELERY_BROKER_URL)


r = redis.StrictRedis(host=redis_url.hostname, port=redis_url.port, db=int(redis_url.path.lstrip('/')))

# --------------------Register---------------------------------------------------
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'date_of_birth', 'phone_number', 'email', 'password', 'confirm_password']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data , is_doctor=False )

        Patient.objects.create(user=user)
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    verification_code = serializers.CharField(write_only=True)

# -----------------------------Forgot password -----------------------

class ForgetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, email):
        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                raise ValidationError("This email is not active.")
        except User.DoesNotExist:
            raise ValidationError("This email does not exist.")
        return email

from django.contrib.auth.password_validation import validate_password

class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data


#---------------------------------User info -------------------------------

class UserInfoSerializer(ModelSerializer):

    class Meta:
        model = User
        fields = [
            "first_name" , "last_name" , "email"
        ]

# ------------------------------------Token----------------------------------

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        return token

# -----------------------------------Login-------------------------------------

class LoginUserModelSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        redis_key = f'failed_attempts_{email}'
        attempts = r.get(redis_key)
        if attempts and int(attempts) >= 5:
            raise ValidationError("Too many failed login attempts. Try again after 5 minutes.")

        user = authenticate(email=email, password=password)

        if user is None:
            current_attempts = int(attempts) if attempts else 0
            r.setex(redis_key, timedelta(minutes=5), current_attempts + 1)
            raise ValidationError("Invalid email or password")

        r.delete(redis_key)
        attrs['user'] = user
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, email):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this email address.")
        return email

    def save(self):
        request = self.context.get('request')
        user = User.objects.get(email=self.validated_data['email'])
        token = PasswordResetTokenGenerator().make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Generate reset link
        reset_link = f"{request._current_scheme_host}/reset-password/{uid}/{token}/"

        # Send reset email (you can adjust email settings in your project)
        user.email_user(
            subject="Password Reset Request",
            message=f"Click the link below to reset your password:\n{reset_link}",
            from_email=None  # Use default from_email from settings
        )


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            uid = urlsafe_base64_decode(data['uid']).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise ValidationError("Invalid UID or user does not exist.")

        if not PasswordResetTokenGenerator().check_token(user, data['token']):
            raise ValidationError("Invalid or expired token.")

        self.user = user
        return data

    def save(self):
        self.user.set_password(self.validated_data['new_password'])
        self.user.save()



# /**/*/**/*/*//*//**/*//*/**//*/*/**//*/*/*/*/*/*/**//*/*/*/*/**/*/*/*/*//*/**/

# apps/serializers.py
from rest_framework import serializers
from .models import Patient, Doctor, Appointment, Payment, TreatmentRoom, TreatmentRegistration





class DoctorCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True)
    consultation_price = serializers.DecimalField(max_digits=10, decimal_places=2)

    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)

    class Meta:
        model = Doctor
        fields = [
            'id', 'name', 'specialty', 'consultation_price',
            'email', 'password', 'first_name', 'last_name'
        ]

    def create(self, validated_data):
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        first_name = validated_data.pop("first_name")
        last_name = validated_data.pop("last_name")

        user = User.objects.create_user(
            email=email,
            password=password,
            is_doctor=True,
            is_active=True,
            first_name=first_name,
            last_name=last_name,
        )

        doctor = Doctor.objects.create(user=user, **validated_data)
        return doctor


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ['id', 'name', 'specialty','consultation_price']

class ServiceSerializer(serializers.ModelSerializer):
    doctor = DoctorSerializer(read_only=True)
    doctor_id = serializers.PrimaryKeyRelatedField(queryset=Doctor.objects.all(), source='doctor', write_only=True)

    class Meta:
        model = Service
        fields = ['id', 'name', 'price', 'doctor', 'doctor_id']

    def get_doctor(self, obj):
        return {
            "id": obj.doctor.id,
            "name": obj.doctor.user.get_full_name()
        }


class UserForDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'date_of_birth', 'phone_number']



class DoctorDetailSerializer(serializers.ModelSerializer):
    user = UserForDoctorSerializer()
    consultation_price = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = Doctor
        fields = ['id', 'user', 'specialty',  'consultation_price']

class PatientSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    last_visit = serializers.DateTimeField(read_only=True)
    total_due = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    patients_doctor = DoctorDetailSerializer(read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'first_name', 'last_name', 'phone', 'address', 'created_at',
            'patients_doctor', 'balance', 'last_visit', 'total_due', 'total_paid'
        ]



class AppointmentSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)
    doctor = DoctorSerializer(read_only=True)
    referred_by = DoctorSerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    appointment = AppointmentSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = '__all__'

class TreatmentPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreatmentPayment
        fields = "__all__"

class TreatmentRoomSerializer(serializers.ModelSerializer):
    patients = serializers.SerializerMethodField()

    class Meta:
        model = TreatmentRoom
        fields = '__all__'

    def get_patients(self, obj):
        active_regs = obj.treatmentregistration_set.filter(discharged_at__isnull=True)
        return [
            {
                "id": reg.patient.id,
                "registration_id": reg.id,  # ✅ Include this
                "first_name": reg.patient.first_name,
                "last_name": reg.patient.last_name
            } for reg in active_regs
        ]

class TreatmentRegistrationSerializer(serializers.ModelSerializer):
    appointment = AppointmentSerializer(read_only=True)
    treatment_room = TreatmentRoomSerializer(read_only=True)
    total_paid = serializers.SerializerMethodField()
    amount_due = serializers.SerializerMethodField()

    class Meta:
        model = TreatmentRegistration
        fields = '__all__'

    def get_total_paid(self, obj):
        return obj.total_paid()

    def get_amount_due(self, obj):
        return obj.amount_due()

class AppointmentStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['status']

class PatientResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientResult
        fields = '__all__'


class DoctorUserCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    date_of_birth = serializers.DateField()
    phone_number = serializers.CharField()
    specialty = serializers.CharField()

    def create(self, validated_data):
        # Extract user fields
        user = User.objects.create_user(
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            email=validated_data["email"],
            password=validated_data["password"],
            date_of_birth=validated_data["date_of_birth"],
            phone_number=validated_data["phone_number"],
            is_doctor=True,
            is_active=True  # Optional: auto-activate
        )
        # Create doctor profile
        doctor = Doctor.objects.create(
            user=user,
            name=f"{user.first_name} {user.last_name}",
            specialty=validated_data["specialty"]
        )
        return doctor




    def update(self, instance, validated_data):
        # Handle nested user data
        user_data = validated_data.pop('user', {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()

        # Update doctor-specific fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance



class RoomStatusSerializer(serializers.Serializer):
    room_id = serializers.IntegerField()
    room_name = serializers.CharField()
    capacity = serializers.IntegerField()
    patients = serializers.ListField(child=serializers.CharField())


class DoctorPaymentSerializer(serializers.ModelSerializer):
    patient_first_name = serializers.CharField(source='patient.first_name', read_only=True)
    patient_last_name = serializers.CharField(source='patient.last_name', read_only=True)

    doctor_first_name = serializers.CharField(source='patient.patients_doctor.user.first_name', read_only=True)
    doctor_last_name = serializers.CharField(source='patient.patients_doctor.user.last_name', read_only=True)

    amount_paid = serializers.DecimalField(source='amount', max_digits=10, decimal_places=2, read_only=True)
    created_at = serializers.DateTimeField(source='date', read_only=True)
    notes = serializers.CharField(required=False)

    class Meta:
        model = TreatmentPayment
        fields = [
            'id',
            'patient_first_name',
            'patient_last_name',
            'doctor_first_name',
            'doctor_last_name',
            'amount_paid',
            'status',
            'created_at',
            'notes',
        ]




class CashRegisterSerializer(serializers.ModelSerializer):
    service_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    services = serializers.SerializerMethodField(read_only=True)
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = CashRegister
        fields = [
            'id',
            'patient_name',
            'transaction_type',
            'payment_method',
            'amount',
            'created_at',
            'services',
            'service_ids',
            'patient'
        ]

    def get_patient_name(self, obj):
        if obj.patient:
            return f"{obj.patient.first_name} {obj.patient.last_name}"
        return "—"

    def create(self, validated_data):
        service_ids = validated_data.pop("service_ids", [])
        services = []

        # ✅ ensure patient is present
        patient = validated_data.get('patient')
        if not patient:
            raise serializers.ValidationError({"patient": "This field is required."})

        if validated_data.get('transaction_type') == 'service' and service_ids:
            services = list(Service.objects.filter(id__in=service_ids))
            if len(services) != len(service_ids):
                raise serializers.ValidationError({"service_ids": "One or more service IDs are invalid"})

            names = ", ".join(s.name for s in services)
            validated_data["notes"] = f"Service Payment: {names}"

        return super().create(validated_data)

    def get_services(self, obj):
        if obj.transaction_type == 'service' and obj.notes and obj.notes.startswith("Service Payment:"):
            names = obj.notes.replace("Service Payment:", "").strip()
            return [name.strip() for name in names.split(",")]
        return []




class CallTurnSerializer(serializers.Serializer):
    appointment_id = serializers.IntegerField()

    class Meta:
        model = TreatmentRegistration
        fields = "__all__"


class TreatmentRegistrationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreatmentRegistration
        fields = ['room']



class TurnNumberSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)

    class Meta:
        model = TurnNumber
        fields = ['doctor', 'doctor_name', 'letter', 'last_number', 'last_reset']

# serializers.py
class TreatmentRoomPaymentReceiptSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    processed_by = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    receipt_number = serializers.SerializerMethodField()
    transaction_type = serializers.SerializerMethodField()

    class Meta:
        model = TreatmentPayment
        fields = [
            "id",
            "receipt_number",
            "date",
            "patient_name",
            "amount",
            "payment_method",
            "status",
            "notes",
            "processed_by",
            "transaction_type",
        ]

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def get_processed_by(self, obj):
        return obj.processed_by.username if obj.processed_by else "—"

    def get_date(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M")

    def get_receipt_number(self, obj):
        return f"TR{obj.id:04}"  # Example: TR0005

    def get_transaction_type(self, obj):
        return "Davolash xonasi"


class OutcomeSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = Outcome
        fields = '__all__'