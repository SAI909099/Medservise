import random
import string
import traceback
from datetime import timedelta

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db.models import Sum, ExpressionWrapper
from django.db.models.functions import Coalesce, ExtractDay, Now
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode
from django.utils.timezone import now
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
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce

from apps.models import User, Doctor, Patient, Appointment, Payment, TreatmentRoom, \
    TreatmentRegistration, PatientResult, Service, TreatmentPayment, CashRegister
from apps.serializers import ForgotPasswordSerializer, PasswordResetConfirmSerializer, RegisterSerializer, \
    LoginSerializer, LoginUserModelSerializer, UserInfoSerializer, DoctorSerializer, \
    PatientSerializer, AppointmentSerializer, PaymentSerializer, TreatmentRoomSerializer, \
    TreatmentRegistrationSerializer, PatientResultSerializer, ServiceSerializer, DoctorCreateSerializer, \
    DoctorUserCreateSerializer, DoctorDetailSerializer, TreatmentPaymentSerializer, DoctorPaymentSerializer, \
    CashRegisterSerializer
from apps.tasks import send_verification_email
from . import models


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
        print("✅ Received patient data:", request.data)  # 🔍 Debug incoming data

        doctor_id = request.data.get("doctor_id")
        if not doctor_id:
            return Response({"error": "Doctor ID is required."}, status=400)

        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor not found"}, status=404)

        patient_data = {
            "first_name": request.data.get("first_name"),
            "last_name": request.data.get("last_name"),
            "phone": request.data.get("phone"),
            "address": request.data.get("address"),
            "age": request.data.get("age"),
        }

        services = request.data.get("services", [])
        reason = request.data.get("reason")
        amount_paid = float(request.data.get("amount_paid", 0))
        amount_owed = float(request.data.get("amount_owed", 0))

        patient_serializer = PatientSerializer(data=patient_data)

        if patient_serializer.is_valid():
            # ✅ Save and assign doctor
            patient = patient_serializer.save(patients_doctor=doctor)
            print("✅ Patient saved:", patient)

            # ✅ Create appointment
            appointment = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                reason=reason,
                status='queued'
            )
            print("✅ Appointment created:", appointment)

            # ✅ Attach selected services
            for service_id in services:
                try:
                    service = Service.objects.get(id=service_id)
                    appointment.services.add(service)
                except Service.DoesNotExist:
                    print(f"⚠️ Service ID {service_id} not found")

            # ✅ Record initial payment
            Payment.objects.create(
                appointment=appointment,
                amount_paid=amount_paid,
                amount_due=amount_owed,
                status='partial' if amount_owed > 0 else 'paid'
            )

            return Response(AppointmentSerializer(appointment).data, status=201)

        else:
            print("❌ Patient serializer errors:", patient_serializer.errors)
            return Response(patient_serializer.errors, status=400)


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

            # Check if room is full
            active_regs = TreatmentRegistration.objects.filter(room=room, discharged_at__isnull=True).count()
            if active_regs >= room.capacity:
                return Response({"error": "Room is full"}, status=400)

            appointment = Appointment.objects.filter(patient=patient).latest("created_at")
            print("✅ Latest appointment:", appointment)

            TreatmentRegistration.objects.create(
                patient=patient,
                room=room,
                appointment=appointment,
                total_paid=room.price_per_day,
                assigned_at=now()
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


class ServiceDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]

@extend_schema(tags=['Doctor'])
class DoctorRegistrationAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = DoctorCreateSerializer(data=request.data)  # ✅ USE THIS INSTEAD
        if serializer.is_valid():
            doctor = serializer.save()
            return Response({"message": "Doctor registered successfully."}, status=201)
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





class TreatmentRoomList(ListAPIView):
    queryset = TreatmentRoom.objects.all()
    serializer_class = TreatmentRoomSerializer
    permission_classes = [IsAuthenticated]

@extend_schema(tags=["Treatment Payments"])
class TreatmentRoomPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rooms = TreatmentRoom.objects.all()
        data = []

        for room in rooms:
            registrations = TreatmentRegistration.objects.filter(room=room, discharged_at__isnull=True)
            patients_data = []
            for reg in registrations:
                total_paid = reg.payments.aggregate(total=Sum('amount_paid'))['total'] or 0
                daily_price = room.price_per_day or 0  # Assuming room has a `price` field
                days = (timezone.now().date() - reg.created_at.date()).days or 1
                amount_due = days * daily_price

                if total_paid >= amount_due:
                    status = "paid"
                elif total_paid > 0:
                    status = "partial"
                else:
                    status = "unpaid"

                patients_data.append({
                    "patient_id": reg.patient.id,
                    "patient_name": f"{reg.patient.first_name} {reg.patient.last_name}",
                    "amount_due": amount_due,
                    "amount_paid": total_paid,
                    "status": status,
                })

            data.append({
                "room_id": room.id,
                "room_name": room.name,
                "floor": room.floor,
                "patients": patients_data
            })

        return Response(data)


@extend_schema(tags=["Treatment Payments"])
class TreatmentRoomPaymentsView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TreatmentPaymentSerializer# ✅ replace with your serializer

    def get(self, request):
        rooms_data = []

        rooms = TreatmentRoom.objects.all()
        for room in rooms:
            active_regs = TreatmentRegistration.objects.filter(
                room=room, discharged_at__isnull=True
            ).select_related("patient")

            patients_data = []
            for reg in active_regs:
                patient = reg.patient

                payments = TreatmentPayment.objects.filter(patient=patient).order_by("date")
                total_paid = sum(p.amount for p in payments)
                expected = reg.total_paid

                if total_paid == 0:
                    status_str = "unpaid"
                elif total_paid < expected:
                    status_str = "partial"
                elif total_paid == expected:
                    status_str = "paid"
                else:
                    status_str = "prepaid"

                overpaid_amount = max(0, total_paid - expected)

                patients_data.append({
                    "id": patient.id,
                    "first_name": patient.first_name,
                    "last_name": patient.last_name,
                    "payments": TreatmentPaymentSerializer(payments, many=True).data,
                    "total_paid": float(total_paid),
                    "expected": float(expected),
                    "status": status_str,
                    "overpaid_amount": float(overpaid_amount),
                })

            rooms_data.append({
                "id": room.id,
                "name": room.name,
                "floor": room.floor,
                "price": float(room.price_per_day),
                "patients": patients_data,
            })

        return Response(rooms_data)

    def post(self, request, *args, **kwargs):
        print("🔥 Incoming POST:", request.data)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            print("❌ Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=400)

@extend_schema(tags=["Doctor Payments"])
class DoctorPaymentsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            payments = TreatmentPayment.objects.select_related(
                'patient__patients_doctor__user'
            ).all().order_by("-date")  # <-- changed here
            serializer = DoctorPaymentSerializer(payments, many=True)
            return Response(serializer.data)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@extend_schema(tags=["Doctor Payments"])
class DoctorPaymentListView(APIView):
    permission_classes = [IsAuthenticated]


    def get(self, request):
        # Select related fields to avoid extra DB hits for nested serializers
        payments = TreatmentPayment.objects.select_related(
            'patient__patients_doctor__user'
        ).all().order_by("-date")
        serializer = DoctorPaymentSerializer(payments, many=True)
        return Response(serializer.data)

class CashRegistrationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        patients = Patient.objects.annotate(
            total_paid=Coalesce(Sum('treatmentpayment__amount'), 0),
            services_value=Coalesce(Sum('appointment__services__price'), 0),
            room_charges=Coalesce(Sum(
                ExpressionWrapper(
                    F('treatmentregistration__room__price_per_day') *
                    (ExtractDay(Now() - F('treatmentregistration__assigned_at')) + 1),
                    output_field=DecimalField()
                )
            ), 0),
            total_due=F('services_value') + F('room_charges'),
            balance=F('total_due') - F('total_paid')
        ).select_related(
            'patients_doctor'
        ).prefetch_related(
            'appointment_set__services',
            'treatmentregistration_set__room'
        )

        def post(self, request):
            serializer = CashRegisterSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=201)
            return Response(serializer.errors, status=400)

        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)


class CashRegistrationView(ListCreateAPIView):
    serializer_class = CashRegisterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CashRegister.objects.filter(
            patient_id=self.kwargs.get('patient_id')
        ).select_related('patient', 'created_by')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # Calculate totals
        total_paid = queryset.aggregate(total=Sum('amount'))['total'] or 0
        patient = Patient.objects.get(id=self.kwargs.get('patient_id'))

        # Calculate patient's balance (you'll need to implement this based on your business logic)
        balance = self.calculate_patient_balance(patient)

        response_data = {
            'transactions': serializer.data,
            'summary': {
                'total_paid': total_paid,
                'balance': balance,
                'patient': {
                    'id': patient.id,
                    'name': f"{patient.first_name} {patient.last_name}",
                    'phone': patient.phone
                }
            }
        }
        return Response(response_data)

    def calculate_patient_balance(self, patient):
        """Calculate the patient's outstanding balance"""
        # Implement your balance calculation logic here
        # This might involve:
        # - Sum of all services/treatments
        # - Minus payments made
        return 0  # Placeholder


class CashRegisterReceiptView(RetrieveAPIView):
    queryset = CashRegister.objects.all()
    serializer_class = CashRegisterSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Generate receipt data
        receipt_data = {
            'receipt_number': instance.reference or f"CR-{instance.id}",
            'date': instance.created_at.strftime("%Y-%m-%d %H:%M"),
            'patient_name': f"{instance.patient.first_name} {instance.patient.last_name}",
            'transaction_type': instance.get_transaction_type_display(),
            'amount': float(instance.amount),
            'payment_method': instance.get_payment_method_display(),
            'processed_by': instance.created_by.get_full_name(),
            'notes': instance.notes
        }

        return Response(receipt_data)

class RecentPatientsByDaysView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 1))  # ?days=1 or 3 or 7
        since_date = timezone.now() - timedelta(days=days)
        patients = Patient.objects.filter(created_at__gte=since_date)
        return Response(PatientSerializer(patients, many=True).data)

class CashRegisterListAPIView(ListAPIView):
    queryset = CashRegister.objects.select_related("patient", "created_by").all()
    serializer_class = CashRegisterSerializer
    permission_classes = [IsAuthenticated]

class CashRegisterListCreateAPIView(ListCreateAPIView):
    queryset = CashRegister.objects.all().order_by('-created_at')
    serializer_class = CashRegisterSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def post(self, request, *args, **kwargs):
        print("🔥 Incoming POST:", request.data)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("❌ Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=400)

        self.perform_create(serializer)
        return Response(serializer.data, status=201)

class RecentPatientsAPIView(APIView):
    def get(self, request):
        days = int(request.GET.get("days", 1))
        since = timezone.now() - timedelta(days=days)
        patients = Patient.objects.filter(created_at__gte=since)
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)


class RecentPatientsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 1))  # defaults to 1 day
        since = timezone.now() - timedelta(days=days)
        patients = Patient.objects.filter(created_at__gte=since).order_by("-created_at")
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)