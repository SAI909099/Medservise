import random
import string
from datetime import timedelta

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView, RetrieveAPIView, \
    ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from apps.models import User, Doctor, Patient, Appointment, Payment, TreatmentRoom, \
    TreatmentRegistration, PatientResult, Service
from apps.serializers import ForgotPasswordSerializer, PasswordResetConfirmSerializer, RegisterSerializer, \
    LoginSerializer, LoginUserModelSerializer, UserInfoSerializer, DoctorSerializer, \
    PatientSerializer, AppointmentSerializer, PaymentSerializer, TreatmentRoomSerializer, \
    TreatmentRegistrationSerializer, PatientResultSerializer, ServiceSerializer, DoctorCreateSerializer, \
    DoctorUserCreateSerializer, DoctorDetailSerializer
from apps.tasks import send_verification_email


# ------------------------------------Register ------------------------------------------
@extend_schema(tags=['Login-Register'])
class RegisterAPIView(APIView):
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Generate a random 6-digit verification code
            verification_code = ''.join(random.choices(string.digits, k=6))
            user.reset_token = verification_code
            user.save()

            # Send the email asynchronously with Celery
            send_verification_email.delay(user.email, verification_code)

            return Response({"message": "User registered successfully. Check your email for the verification code."},
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework.response import Response


@extend_schema(tags=['Login-Register'])
class VerifyEmailAPIView(APIView):
    serializer_class = LoginSerializer

    def post(self, request):
        # print("Request data:", request.data)  # Debugging the incoming data
        email = request.data.get('email')
        verification_code = request.data.get('verification_code') or request.data.get('password')  # Temporary fix

        # print("Request data:", request.data)  # This should now include 'verification_code'
        # print("Verification Code:", request.data.get('verification_code'))

        if not email or not verification_code:
            return Response({"error": "Email and verification code are required."}, status=400)

        try:
            user = User.objects.get(email=email, reset_token=verification_code)
            user.is_active = True
            user.reset_token = ''
            user.save()
            return Response({"message": "Email verified successfully."}, status=200)
        except User.DoesNotExist:
            return Response({"error": "Invalid email or verification code."}, status=400)


@extend_schema(tags=['Login-Register'])
class LoginAPIView(GenericAPIView):
    serializer_class = LoginUserModelSerializer
    permission_classes = [AllowAny]
    authentication_classes = ()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)


@extend_schema(tags=['Access-Token'])
class ActivateUserView(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            uid, is_active = uid.split('/')
            user = User.objects.get(pk=uid, is_active=is_active)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user and PasswordResetTokenGenerator().check_token(user, token):
            user.is_active = True
            user.save()
            return Response({"message": "User successfully verified!"})
        raise AuthenticationFailed('The link is invalid or expired.')


# -------------------------------Forgot password---------------------------------
class ForgotPasswordView(GenericAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password reset link has been sent to your email."}, status=status.HTTP_200_OK)


# ------------------------------------------------------------------

class PasswordResetConfirmView(GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)


# ----------------------------------User info -------------------------------


@extend_schema(tags=['user'])
class UserInfoListCreateAPIView(ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserInfoSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return super().get_queryset().filter(id=self.request.user.id)



# /*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/**/*/*/*/*/*/*/*/*/*/*/*//*/*/*-/
@extend_schema(tags=['Patient'])
class PatientRegistrationAPIView(APIView):
    @extend_schema(
        tags=["Registration"],
        request=PatientSerializer,
        responses={201: AppointmentSerializer}
    )
    def post(self, request):
        # Extract patient data
        patient_data = {
            "first_name": request.data.get("first_name"),
            "last_name": request.data.get("last_name"),
            "phone": request.data.get("phone"),
            "address": request.data.get("address")
        }
        reason = request.data.get("reason")
        doctor_id = request.data.get("doctor_id")

        patient_serializer = PatientSerializer(data=patient_data)
        if patient_serializer.is_valid():
            patient = patient_serializer.save()

            # Create appointment
            try:
                doctor = Doctor.objects.get(id=doctor_id)
            except Doctor.DoesNotExist:
                return Response({"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)

            appointment = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                reason=reason,
                status='queued'
            )
            return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)

        return Response(patient_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
@extend_schema(tags=['Doctor'])
class DoctorListCreateAPIView(ListCreateAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return super().get_queryset()

@extend_schema(tags=['Appointment'])
class AppointmentListCreateAPIView(ListCreateAPIView):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer

@extend_schema(tags=['Payment'])
class PaymentListCreateAPIView(ListCreateAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

@extend_schema(tags=['Treatment'])
class TreatmentRoomListCreateAPIView(ListCreateAPIView):
    queryset = TreatmentRoom.objects.all()
    serializer_class = TreatmentRoomSerializer

@extend_schema(tags=['Treatment-register'])
class TreatmentRegistrationListCreateAPIView(ListCreateAPIView):
    queryset = TreatmentRegistration.objects.all()
    serializer_class = TreatmentRegistrationSerializer

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from .models import Appointment
from .serializers import AppointmentSerializer


@extend_schema(tags=["Doctor Appointments"])
class DoctorAppointmentListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # ✅ Check if user is marked as a doctor
        if not getattr(user, 'is_doctor', False):
            return Response({"error": "Only doctors can access this endpoint"}, status=403)

        # ✅ Safely get the Doctor profile linked to this user
        try:
            doctor = Doctor.objects.get(user=user)
        except Doctor.DoesNotExist:
            return Response({"error": "This user is not linked to a Doctor profile"}, status=404)

        # ✅ Get appointments for this doctor
        appointments = Appointment.objects.filter(doctor=doctor).order_by("created_at")
        serializer = AppointmentSerializer(appointments, many=True)

        # ✅ Count how many are still queued
        queued_count = appointments.filter(status="queued").count()

        return Response({
            "total_appointments": appointments.count(),
            "queued_patients": queued_count,
            "appointments": serializer.data
        })


@extend_schema(tags=["Doctor Appointments"])
class DoctorAppointmentDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Only allow doctor to access their own appointments
        return Appointment.objects.filter(doctor__user=self.request.user)

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Appointment deleted successfully."}, status=status.HTTP_204_NO_CONTENT)



@extend_schema(tags=["Doctor Appointments"])
class AssignPatientToRoomAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        patient_id = request.data.get("patient_id")
        room_id = request.data.get("room_id")

        if not patient_id or not room_id:
            return Response({"error": "Both patient_id and room_id are required"}, status=400)

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found"}, status=404)

        try:
            room = TreatmentRoom.objects.get(id=room_id)
        except TreatmentRoom.DoesNotExist:
            return Response({"error": "Treatment room not found"}, status=404)

        # Check if room is full
        current_occupants = TreatmentRegistration.objects.filter(room=room, discharged_at__isnull=True).count()
        if current_occupants >= room.capacity:
            return Response({"error": "Room is full"}, status=400)

        # Create registration
        TreatmentRegistration.objects.create(patient=patient, room=room)

        return Response({"message": "Patient assigned to room successfully"}, status=200)

@extend_schema(tags=["Treatment"])
class AssignRoomAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("📥 Incoming data:", request.data)

        patient_id = request.data.get("patient_id")
        room_id = request.data.get("room_id")

        if not patient_id or not room_id:
            print("❌ Missing data")
            return Response({"error": "Missing patient_id or room_id"}, status=400)

        try:
            patient = Patient.objects.get(id=patient_id)
            print("✅ Found patient:", patient)

            room = TreatmentRoom.objects.get(id=room_id)
            print("✅ Found room:", room)

            appointment = Appointment.objects.filter(patient=patient).latest("created_at")
            print("✅ Latest appointment:", appointment)

            TreatmentRegistration.objects.create(
                appointment=appointment,
                patient=patient,
                room=room
            )

            return Response({"message": "Patient assigned successfully"}, status=200)

        except Patient.DoesNotExist:
            print("❌ Patient not found")
            return Response({"error": "Patient not found"}, status=404)

        except Appointment.DoesNotExist:
            print("❌ No appointment found for patient")
            return Response({"error": "No appointment found for patient"}, status=404)

        except TreatmentRoom.DoesNotExist:
            print("❌ Room not found")
            return Response({"error": "Room not found"}, status=404)

        except Exception as e:
            print("❌ Unexpected error:", str(e))
            return Response({"error": str(e)}, status=500)



@extend_schema(tags=['Treatment'])
class TreatmentRoomDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = TreatmentRoom.objects.all()
    serializer_class = TreatmentRoomSerializer
    permission_classes = [IsAuthenticated]

class PatientResultListCreateAPIView(ListCreateAPIView):
    queryset = PatientResult.objects.all()
    serializer_class = PatientResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        return queryset

class PatientResultDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = PatientResult.objects.all()
    serializer_class = PatientResultSerializer
    permission_classes = [IsAuthenticated]

class PatientDetailAPIView(RetrieveAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer

class PatientListAPIView(ListAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]


class ServiceListCreateAPIView(ListCreateAPIView):
    queryset = Service.objects.select_related('doctor').all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]


@extend_schema(tags=['Doctor'])
class DoctorRegistrationAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = DoctorCreateSerializer(data=request.data)
        if serializer.is_valid():
            doctor = serializer.save()
            return Response({"message": "Doctor registered successfully"}, status=201)
        return Response(serializer.errors, status=400)


class CreateDoctorWithUserView(APIView):
    permission_classes = [IsAuthenticated]  # Optional: or AllowAny

    def post(self, request):
        serializer = DoctorUserCreateSerializer(data=request.data)
        if serializer.is_valid():
            doctor = serializer.save()
            return Response({"message": "Doctor created successfully."})
        return Response(serializer.errors, status=400)


class DoctorDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorDetailSerializer
    permission_classes = [IsAuthenticated]


class RoomStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = []
        rooms = TreatmentRoom.objects.all()
        for room in rooms:
            active_regs = TreatmentRegistration.objects.filter(room=room, discharged_at__isnull=True)
            patient_names = [f"{reg.patient.first_name} {reg.patient.last_name}" for reg in active_regs]
            data.append({
                "room_id": room.id,
                "room_name": room.name,
                "capacity": room.capacity,
                "patients": patient_names
            })
        return Response(data)


@property
def is_active(self):
    return self.discharged_at is None



class RecentPatientsView(ListAPIView):
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        two_days_ago = timezone.now() - timedelta(days=2)
        return Patient.objects.filter(created_at__gte=two_days_ago)

class TreatmentRoomList(ListAPIView):
    queryset = TreatmentRoom.objects.all()
    serializer_class = TreatmentRoomSerializer
    permission_classes = [IsAuthenticated]
