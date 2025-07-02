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
from .models import User, Doctor, Patient, PatientResult, Service

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

    class Meta:
        model = Doctor
        fields = ['id', 'name', 'specialty', 'consultation_price', 'email', 'password']

    def create(self, validated_data):
        email = validated_data.pop("email")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            email=email,
            password=password,
            is_doctor=True,
            is_active=True,
        )

        # ✅ consultation_price is now included
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

class PatientSerializer(serializers.ModelSerializer):
    latest_doctor = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = ['id', 'first_name', 'last_name', 'phone', 'address', 'created_at', 'latest_doctor']

    def get_latest_doctor(self, patient):
        latest_appointment = Appointment.objects.filter(patient=patient).order_by('-created_at').first()
        return latest_appointment.doctor.name if latest_appointment and latest_appointment.doctor else "N/A"




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