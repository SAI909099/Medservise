import random
import string
import json
from decimal import Decimal
from escpos.printer import Win32Raw
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
)
from django.db.models.functions import (
    Coalesce,
    ExtractDay,
    Now,
)
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode
from django.utils.timezone import localtime

from drf_spectacular.utils import extend_schema
from escpos.printer import Usb

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import (
    GenericAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    RetrieveAPIView,
    ListAPIView,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.status import HTTP_201_CREATED
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.models import (
    User,
    Doctor,
    Patient,
    Appointment,
    Payment,
    TreatmentRoom,
    TreatmentRegistration,
    PatientResult,
    Service,
    TreatmentPayment,
    CashRegister,
    TurnNumber,
    CurrentCall,
)
from apps.serializers import (
    ForgotPasswordSerializer,
    PasswordResetConfirmSerializer,
    RegisterSerializer,
    LoginSerializer,
    LoginUserModelSerializer,
    UserInfoSerializer,
    DoctorSerializer,
    PatientSerializer,
    AppointmentSerializer,
    PaymentSerializer,
    TreatmentRoomSerializer,
    TreatmentRegistrationSerializer,
    PatientResultSerializer,
    ServiceSerializer,
    DoctorCreateSerializer,
    DoctorUserCreateSerializer,
    DoctorDetailSerializer,
    TreatmentPaymentSerializer,
    DoctorPaymentSerializer,
    CashRegisterSerializer,
    CallTurnSerializer,
)
from apps.tasks import send_verification_email
from utils.receipt_printer import ReceiptPrinter

from .models import Outcome
from .serializers import OutcomeSerializer
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from .models import LabRegistration
from .serializers import LabRegistrationSerializer


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
            'role': user.role if hasattr(user, 'role') else None,
            'is_admin': user.is_superuser  # or user.is_admin if you have that field
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
        print("✅ Received patient data:", request.data)

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

            # ✅ Ensure TurnNumber with letter exists
            turn_instance, created = TurnNumber.objects.get_or_create(doctor=doctor)
            if created or not turn_instance.letter:
                used_letters = set(TurnNumber.objects.exclude(letter=None).values_list("letter", flat=True))
                for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    if letter not in used_letters:
                        turn_instance.letter = letter
                        break
                else:
                    return Response({"error": "No available letters for doctor turn codes."}, status=400)
                turn_instance.save()

            # ✅ Generate turn number
            try:
                turn_code = turn_instance.get_next_turn()
            except Exception as e:
                print("❌ Turn number generation failed:", e)
                return Response({"error": "Failed to generate turn number."}, status=400)

            # ✅ Create appointment
            appointment = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                reason=reason,
                status='queued',
                turn_number=turn_code
            )
            print("✅ Appointment created:", appointment)

            # ✅ Attach services
            for service_id in services:
                try:
                    service = Service.objects.get(id=service_id)
                    appointment.services.add(service)
                except Service.DoesNotExist:
                    print(f"⚠️ Service ID {service_id} not found")

            # ✅ Record payment
            Payment.objects.create(
                appointment=appointment,
                amount_paid=amount_paid,
                amount_due=amount_owed,
                status='partial' if amount_owed > 0 else 'paid'
            )

            # ✅ Response
            response_data = AppointmentSerializer(appointment).data
            response_data["turn_number"] = appointment.turn_number
            response_data["doctor_name"] = doctor.user.get_full_name()

            return Response(response_data, status=HTTP_201_CREATED)

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
    queryset = Patient.objects.all().order_by('-created_at')
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
        data = request.data.copy()
        role = data.get("role")

        # Ensure all roles are mutually exclusive
        data["is_doctor"] = role == "doctor"
        data["is_cashier"] = role == "cashier"
        data["is_accountant"] = role == "accountant"
        data["is_registrator"] = role == "registration"
        data["is_superuser"] = role == "admin"

        serializer = DoctorCreateSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Foydalanuvchi muvaffaqiyatli ro'yxatdan o'tkazildi."}, status=201)
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
    serializer_class = TreatmentPaymentSerializer  # ✅ replace with your serializer

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


import logging
logger = logging.getLogger(__name__)


class CashRegistrationView(ListCreateAPIView):
    serializer_class = CashRegisterSerializer
    permission_classes = [IsAuthenticated]



    def get_queryset(self):
        patient_id = self.kwargs.get('patient_id')
        return CashRegister.objects.filter(
            patient_id=patient_id
        ).select_related('patient', 'created_by')

    def list(self, request, *args, **kwargs):
        patient_id = self.kwargs.get('patient_id')

        try:
            # ✅ Make sure this line exists and is above where 'patient' is used
            patient = Patient.objects.select_related('patients_doctor__user').prefetch_related('services').get(
                id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found"}, status=404)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        total_paid = queryset.aggregate(
            total=Sum(ExpressionWrapper(F('amount'), output_field=DecimalField()))
        )['total'] or Decimal('0.00')

        doctor_data = DoctorDetailSerializer(patient.patients_doctor).data if patient.patients_doctor else None
        latest_service = patient.services.last()
        service_data = ServiceSerializer(latest_service).data if latest_service else None

        balance = self.calculate_patient_balance(patient)

        return Response({
            'transactions': serializer.data,
            'summary': {
                'total_paid': total_paid,
                'balance': balance,
                'patient': {
                    'id': patient.id,
                    'name': f"{patient.first_name} {patient.last_name}",
                    'phone': patient.phone,
                    'patients_doctor': doctor_data,
                    'patients_service': service_data,
                }
            }
        })

    def calculate_patient_balance(self, patient):
        # If the patient has a doctor, return only the consultation price
        if patient.patients_doctor:
            consultation_price = patient.patients_doctor.consultation_price or Decimal('0.00')
            return consultation_price

        # Else if they have a specific service (like lab, ultrasound)
        latest_service = patient.services.last()
        if latest_service:
            return latest_service.price

        # Fallback to treatment room charges only
        return self._get_room_charges(patient)

    def _get_room_charges(self, patient):
        active_regs = TreatmentRegistration.objects.filter(
            patient=patient,
            discharged_at__isnull=True
        )
        days_expr = ExpressionWrapper(
            ExtractDay(Now() - F('assigned_at')) + 1,
            output_field=DecimalField(max_digits=5, decimal_places=2)
        )
        cost_expr = ExpressionWrapper(
            F('room__price_per_day') * days_expr,
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
        return active_regs.aggregate(total=Sum(cost_expr))['total'] or Decimal('0.00')



class CashRegisterReceiptView(RetrieveAPIView):
    queryset = CashRegister.objects.all()
    serializer_class = CashRegisterSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        doctor = instance.patient.patients_doctor
        doctor_name = f"{doctor.user.first_name} {doctor.user.last_name}" if doctor else None

        # Generate receipt data
        receipt_data = {
            'receipt_number': instance.reference or f"CR-{instance.id}",
            'date': instance.created_at.strftime("%Y-%m-%d %H:%M"),
            'patient_name': f"{instance.patient.first_name} {instance.patient.last_name}",
            'doctor_name': doctor_name,
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
        transaction_type = self.request.data.get("transaction_type")
        prefix = "A" if transaction_type == "consultation" else "B"
        last = CashRegister.objects.filter(reference__startswith=prefix).order_by("-id").first()

        # Get last number and increment
        if last and last.turn_number:
            last_number = int(last.turn_number[1:])
        else:
            last_number = 0

        new_turn_number = f"{prefix}{last_number + 1:03d}"
        serializer.save(created_by=self.request.user, turn_number=new_turn_number)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        instance = serializer.save(created_by=self.request.user)

        # ✅ Prepare receipt data
        receipt_data = {
            'receipt_number': instance.reference or f"CR-{instance.id}",
            'date': localtime(instance.created_at).strftime("%Y-%m-%d %H:%M"),
            'patient_name': f"{instance.patient.first_name} {instance.patient.last_name}",
            'transaction_type': instance.get_transaction_type_display(),
            'amount': float(instance.amount),
            'payment_method': instance.get_payment_method_display(),
            'processed_by': instance.created_by.get_full_name(),
            'notes': instance.notes or ""
        }

        # ✅ Print receipt
        try:
            printer = ReceiptPrinter()
            printer.print_receipt(receipt_data)
        except Exception as e:
            print("🖨️ Error printing receipt:", e)

        return Response(self.get_serializer(instance).data, status=201)


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
        days = int(request.query_params.get("days", 1))
        since = timezone.now() - timedelta(days=days)
        patients = Patient.objects.filter(created_at__gte=since).order_by("-created_at")

        # Optionally exclude incomplete patients
        patients = patients.exclude(first_name__isnull=True).exclude(last_name__isnull=True)

        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)


# ✅ 1. List and Create Treatment Assignments
class TreatmentRegistrationListCreateView(ListCreateAPIView):
    queryset = TreatmentRegistration.objects.filter(discharged_at__isnull=True)
    serializer_class = TreatmentRegistrationSerializer

    def perform_create(self, serializer):
        serializer.save()


# ✅ 2. Discharge a Patient from the Room (sets discharged_at)
class TreatmentDischargeView(APIView):
    def post(self, request, pk):
        registration = get_object_or_404(TreatmentRegistration, pk=pk, discharged_at__isnull=True)
        registration.discharged_at = now()
        registration.save()
        return Response({"detail": "✅ Patient discharged."}, status=status.HTTP_200_OK)


# ✅ 3. Move Patient to Another Room


class TreatmentMoveView(APIView):
    def post(self, request, pk):
        old_reg = get_object_or_404(TreatmentRegistration, pk=pk, discharged_at__isnull=True)
        new_room_id = request.data.get("room_id")

        if not new_room_id:
            return Response({"error": "room_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_room = TreatmentRoom.objects.get(pk=new_room_id)
        except TreatmentRoom.DoesNotExist:
            return Response({"error": "Invalid room ID"}, status=status.HTTP_404_NOT_FOUND)

        # 1. Discharge current
        old_reg.discharged_at = now()
        old_reg.save()

        # 2. Create new registration (same patient & appointment)
        TreatmentRegistration.objects.create(
            patient=old_reg.patient,
            room=new_room,
            appointment=old_reg.appointment,
            assigned_at=old_reg.assigned_at,
        )

        return Response({"detail": "✅ Patient moved to new room."}, status=status.HTTP_200_OK)


class DoctorPatientRoomView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        doctor = request.user.doctor
        patients = Patient.objects.filter(patients_doctor=doctor)
        data = []

        for patient in patients:
            # Only include if patient is currently in treatment room
            reg = TreatmentRegistration.objects.filter(patient=patient, discharged_at__isnull=True).first()
            if reg and reg.room:
                data.append({
                    "id": patient.id,
                    "first_name": patient.first_name,
                    "last_name": patient.last_name,
                    "room": reg.room.name,
                    "floor": reg.room.floor
                })

        return Response(data)


class GenerateTurnView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            doctor = Doctor.objects.get(user=user)
        except Doctor.DoesNotExist:
            return Response({"detail": "Siz shifokor emassiz"}, status=status.HTTP_403_FORBIDDEN)

        turn_number_obj, _ = TurnNumber.objects.get_or_create(doctor=doctor, defaults={
            "letter": self.assign_letter(),
        })

        next_turn = turn_number_obj.get_next_turn()
        return Response({
            "doctor": doctor.user.get_full_name(),
            "turn_number": next_turn
        })

    def assign_letter(self):
        # Assign next available letter A-Z to the doctor
        used_letters = set(TurnNumber.objects.values_list('letter', flat=True))
        for char in map(chr, range(65, 91)):  # A-Z
            if char not in used_letters:
                return char
        raise ValueError("No letters available")


class CallPatientView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, appointment_id):
        try:
            appointment = Appointment.objects.get(id=appointment_id, doctor=request.user.doctor)
        except Appointment.DoesNotExist:
            return Response({"error": "Appointment not found"}, status=404)

        # Always update or create call with latest timestamp
        CurrentCall.objects.update_or_create(
            appointment=appointment,
            defaults={"called_at": timezone.now()}
        )

        return Response({"message": "Patient called (or recalled)"})

class CurrentCallsView(APIView):
    def get(self, request):
        doctor_calls = []
        service_calls = []
        queued = []

        # Called patients
        for call in CurrentCall.objects.select_related('appointment__patient', 'appointment__doctor'):
            appointment = call.appointment
            patient = appointment.patient
            turn = getattr(appointment, "turn_number", None)
            if not turn:
                continue
            entry = {
                "id": appointment.id,
                "turn_number": turn,
                "patient_name": f"{patient.first_name} {patient.last_name}"
            }
            if turn.startswith("A"):
                doctor_calls.append(entry)
            elif turn.startswith("B"):
                service_calls.append(entry)

        # Queued patients not yet called
        called_ids = CurrentCall.objects.values_list("appointment_id", flat=True)
        queued_apps = Appointment.objects.filter(status="queued").exclude(id__in=called_ids).select_related("patient", "doctor")

        for app in queued_apps:
            if not app.turn_number:
                continue
            queued.append({
                "turn_number": app.turn_number,
                "patient_name": f"{app.patient.first_name} {app.patient.last_name}"
            })

        return Response({
            "doctor_calls": doctor_calls,
            "service_calls": service_calls,
            "queued": queued
        })

@extend_schema(request=CallTurnSerializer, tags=["Turn"])
class CallTurnView(APIView):
    def post(self, request):
        appointment_id = request.data.get("appointment_id")
        if not appointment_id:
            return Response({"error": "appointment_id required"}, status=400)

        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response({"error": "Appointment not found"}, status=404)

        CurrentCall.objects.update_or_create(
            appointment=appointment,
            defaults={"called_at": timezone.now()}
        )

        return Response({"success": True, "message": "Patient called"})



class PrintTurnView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        patient_name = request.data.get("patient_name")
        doctor_name = request.data.get("doctor_name")
        turn_number = request.data.get("turn_number")
        patient_id = request.data.get("patient_id")  # 👈 You need to send this from frontend

        if not all([patient_name, doctor_name, turn_number, patient_id]):
            return Response({"error": "Missing fields"}, status=400)

        try:
            p = Win32Raw("ReceiptPrinter")  # 👈 Must match Windows printer name

            # Header
            p.set(align='center', bold=True, width=2, height=2)
            p.text("Controllab Clinic\n")

            # Body
            p.set(align='left', bold=False, width=1, height=1)
            p.text("--------------------------------\n")
            p.text(f"Bemor: {patient_name}\n")
            p.text(f"Shifokor: {doctor_name}\n")
            p.text(f"Sana: {timezone.now().strftime('%Y-%m-%d %H:%M')}\n")
            p.text("--------------------------------\n")

            # Footer
            p.set(align='center', bold=True)
            p.text("Iltimos navbatni kuting\n\n")

            p.set(width=8, height=8, bold=True)
            p.text(f"{turn_number}\n\n")

            # New QR code pointing to patient detail page
            location_url = f"http://yourdomain.com/patient/detail/{patient_id}/"
            p.qr(location_url, size=10)
            p.text(" Bemor haqida ma'lumot \n")
            p.cut()

            return Response({"message": "Printed ✅"})
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class ClearCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, appointment_id):
        try:
            call = CurrentCall.objects.get(appointment_id=appointment_id)
            call.delete()
            return Response({"message": "Call cleared"})
        except CurrentCall.DoesNotExist:
            return Response({"error": "Call not found"}, status=404)



class AdminStatisticsView(APIView):
    def get(self, request):
        start_date_raw = request.GET.get('start_date')
        end_date_raw = request.GET.get('end_date')

        start_date = parse_date(start_date_raw) if start_date_raw else None
        end_date = parse_date(end_date_raw) if end_date_raw else None

        # ✅ CashRegister filters
        cash_qs = CashRegister.objects.all()
        if start_date and end_date:
            cash_qs = cash_qs.filter(created_at__date__range=(start_date, end_date))

        # ✅ Treatment room payments
        room_qs = TreatmentPayment.objects.all()
        if start_date and end_date:
            room_qs = room_qs.filter(date__date__range=(start_date, end_date))

        # ✅ Aggregates
        total_profit = cash_qs.aggregate(total=Sum('amount'))['total'] or 0
        treatment_room_profit = room_qs.aggregate(total=Sum('amount'))['total'] or 0

        # ✅ Consultation (doctor) profit
        doctor_profit = cash_qs.filter(transaction_type='consultation').aggregate(total=Sum('amount'))['total'] or 0

        # ✅ Service profit
        service_profit = cash_qs.filter(transaction_type='service').aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            "total_profit": total_profit + treatment_room_profit,
            "treatment_room_profit": treatment_room_profit,
            "doctor_profit": doctor_profit,
            "service_profit": service_profit
        })


class RecentTransactionsView(APIView):
    def get(self, request):
        start_date_raw = request.GET.get('start_date')
        end_date_raw = request.GET.get('end_date')

        start_date = parse_date(start_date_raw) if start_date_raw else now().date() - timedelta(days=30)
        end_date = parse_date(end_date_raw) if end_date_raw else now().date()

        qs = CashRegister.objects.all()
        if start_date and end_date:
            qs = qs.filter(created_at__date__range=(start_date, end_date))

        qs = qs.order_by('-created_at')[:100]

        serializer = CashRegisterSerializer(qs, many=True)
        return Response(serializer.data)

from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.dateparse import parse_date
from .models import CashRegister  # adjust import if needed

class AdminChartDataView(APIView):
    def get(self, request):
        start_raw = request.GET.get('start_date')
        end_raw = request.GET.get('end_date')
        start = parse_date(start_raw) if start_raw else None
        end = parse_date(end_raw) if end_raw else None

        data = {
            "doctors": [],
            "services": [],
            "rooms": []
        }

        qs = CashRegister.objects.all()
        if start and end:
            qs = qs.filter(created_at__date__range=(start, end))

        # Doctor Profit
        doctor_qs = qs.filter(transaction_type='consultation')
        doctors = doctor_qs.values('doctor__name').annotate(profit=Sum('amount'))
        data['doctors'] = [{"name": d['doctor__name'] or "—", "profit": d['profit']} for d in doctors]

        # Service Profit
        service_qs = qs.filter(transaction_type='service')
        for s in service_qs:
            if s.notes and "Service Payment:" in s.notes:
                names = s.notes.replace("Service Payment:", "").split(",")
                for name in names:
                    clean = name.strip()
                    match = next((i for i in data["services"] if i["name"] == clean), None)
                    if match:
                        match["profit"] += s.amount
                    else:
                        data["services"].append({"name": clean, "profit": s.amount})

        # Treatment Room Profit (parse from notes)
        room_qs = qs.filter(transaction_type='treatment')
        for r in room_qs:
            if r.notes and "Room Payment:" in r.notes:
                room_name = r.notes.replace("Room Payment:", "").strip()
                match = next((i for i in data["rooms"] if i["name"] == room_name), None)
                if match:
                    match["profit"] += r.amount
                else:
                    data["rooms"].append({"name": room_name, "profit": r.amount})

        # ➕ Add Monthly Comparison Chart Data
        today = now().date()
        first_day_this_month = today.replace(day=1)
        first_day_last_month = (first_day_this_month - timedelta(days=1)).replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)

        def get_month_data(start, end):
            base_qs = CashRegister.objects.filter(created_at__date__range=(start, end))
            return {
                "doctor_profit": base_qs.filter(transaction_type='consultation').aggregate(total=Sum('amount'))['total'] or 0,
                "service_profit": base_qs.filter(transaction_type='service').aggregate(total=Sum('amount'))['total'] or 0,
                # Optional: Add this if you want room in comparison too
                # "treatment_room_profit": base_qs.filter(transaction_type='treatment').aggregate(total=Sum('amount'))['total'] or 0
            }

        data["monthly_comparison"] = {
            "this_month": get_month_data(first_day_this_month, today),
            "last_month": get_month_data(first_day_last_month, last_day_last_month)
        }

        return Response(data)


# apps/views.py
import logging
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.models import TreatmentPayment, TreatmentRegistration

logger = logging.getLogger(__name__)

class TreatmentPaymentReceiptView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        logger.info(f"Fetching payment with id={id} for user={request.user.id}")
        try:
            # Use _default_manager to bypass custom managers
            payment = get_object_or_404(TreatmentPayment._default_manager, id=id)
            patient = payment.patient
            user = payment.created_by
            logger.info(f"Payment found: id={payment.id}, patient={patient.id}, created_by={user.id if user else None}")

            try:
                registration = TreatmentRegistration.objects.filter(
                    patient=patient, discharged_at__isnull=True
                ).latest("assigned_at")
                doctor = registration.appointment.doctor if registration.appointment else None
                logger.info(f"Registration found: doctor={doctor.id if doctor else None}")
            except TreatmentRegistration.DoesNotExist:
                logger.info(f"No active registration for patient={patient.id}")
                doctor = None
            except Exception as e:
                logger.error(f"Error fetching registration for payment_id={id}: {str(e)}")
                doctor = None

            type_map = {
                'consultation': 'Konsultatsiya',
                'treatment': 'Davolash',
                'service': 'Xizmat',
                'room': 'Xona',
                'other': 'Boshqa'
            }

            method_map = {
                'cash': 'Naqd',
                'card': 'Karta',
                'insurance': 'Sug‘urta',
                'transfer': 'Bank'
            }

            return Response({
                "id": payment.id,
                "receipt_number": f"TP-{payment.id}",
                "date": payment.date.strftime("%Y-%m-%d %H:%M:%S") if payment.date else now().strftime("%Y-%m-%d %H:%M:%S"),
                "amount": float(payment.amount) if payment.amount else 0.0,
                "payment_method": method_map.get(payment.payment_method, payment.payment_method or "unknown"),
                "status": payment.status or "unknown",
                "notes": payment.notes or "",
                "patient_name": f"{patient.first_name} {patient.last_name}".strip() if patient else "Unknown",
                "doctor_name": f"{doctor.first_name} {doctor.last_name}".strip() if doctor else "—",
                "processed_by": user.get_full_name() if user else "Unknown",
                "transaction_type": type_map.get(payment.transaction_type, payment.transaction_type or "treatment")
            }, status=status.HTTP_200_OK)
        except TreatmentPayment.DoesNotExist:
            logger.error(f"TreatmentPayment with id={id} not found")
            return Response({"error": "To‘lov topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Unexpected error in TreatmentPaymentReceiptView for payment_id={id}: {str(e)}")
            return Response({"error": f"Server xatosi: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# apps/views.py
import json
import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.models import TreatmentPayment, TreatmentRegistration
from escpos.printer import Usb

logger = logging.getLogger(__name__)

class PrintTreatmentRoomReceiptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_id = request.data.get("payment_id")
        if not payment_id:
            return Response({"error": "payment_id kiritilmadi"}, status=400)

        try:
            payment = get_object_or_404(TreatmentPayment, id=payment_id)
        except TreatmentPayment.DoesNotExist:
            logger.error(f"TreatmentPayment with id={payment_id} not found")
            return Response({"error": "To‘lov topilmadi"}, status=404)

        try:
            registration = TreatmentRegistration.objects.filter(
                patient=payment.patient, discharged_at__isnull=True
            ).latest("assigned_at")
            doctor = registration.appointment.doctor if registration.appointment else None
        except TreatmentRegistration.DoesNotExist:
            doctor = None
        except Exception as e:
            logger.error(f"Error fetching registration for payment_id={payment_id}: {str(e)}")
            doctor = None

        try:
            p = Usb(0x0483, 0x070b)
            p.set(align='center', text_type='B', width=2, height=2)
            p.text("🏥 NEURO PULS KLINIKASI\n\n")

            p.set(align='left', text_type='B', width=1, height=1)
            p.text(f"Chek raqami: TP-{payment.id}\n")
            p.text(f"Sana      : {payment.date.strftime('%Y-%m-%d %H:%M:%S')}\n")
            p.text(f"Bemor     : {payment.patient.first_name} {payment.patient.last_name}\n")
            p.text(f"Turi      : {payment.transaction_type or 'Davolash'}\n")
            p.text(f"Miqdor    : {float(payment.amount):.0f}.00 so'm\n")
            p.text(f"Usul      : {payment.payment_method or 'N/A'}\n")
            p.text(f"Qabulchi  : {payment.created_by.get_full_name() if payment.created_by else 'N/A'}\n")
            if payment.notes:
                p.text(f"Izoh      : {payment.notes}\n")
            p.text("-----------------------------")
            p.text("Rahmat! Kuningiz yaxshi o‘tsin!\n")

            qr_data = json.dumps({
                "name": f"{payment.patient.first_name} {payment.patient.last_name}",
                "amount": str(payment.amount),
                "payment_method": payment.payment_method,
                "status": payment.status,
                "doctor": doctor.get_full_name() if doctor else "-",
                "note": payment.notes or "",
                "date": payment.date.strftime('%Y-%m-%d %H:%M:%S')
            }, ensure_ascii=False)

            p.text("\n\n")
            p.qr(qr_data, size=6)
            p.text("\n\n\n")
            p.cut()

            return Response({"success": True}, status=200)
        except Exception as e:
            logger.exception(f"❌ USB printerda xatolik for payment_id={payment_id}: {str(e)}")
            return Response({"error": str(e)}, status=500)

class TreatmentRoomStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = now().date()
        current_month = today.month
        current_year = today.year

        # Daily total
        daily_total = TreatmentPayment.objects.filter(date__date=today).aggregate(
            total=Sum("amount")
        )["total"] or 0

        # Monthly total
        monthly_total = TreatmentPayment.objects.filter(
            date__year=current_year, date__month=current_month
        ).aggregate(total=Sum("amount"))["total"] or 0

        # Total all-time
        total_all = TreatmentPayment.objects.aggregate(
            total=Sum("amount")
        )["total"] or 0

        return Response({
            "daily_total": daily_total,
            "monthly_total": monthly_total,
            "total_all": total_all,
        })



class AccountantDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        # Base querysets
        cash_qs = CashRegister.objects.all()
        outcome_qs = Outcome.objects.all()
        treatment_qs = TreatmentPayment.objects.filter(status='paid')

        if start_date and end_date:
            start = parse_date(start_date)
            end = parse_date(end_date)
            cash_qs = cash_qs.filter(created_at__date__range=(start, end))
            outcome_qs = outcome_qs.filter(created_at__date__range=(start, end))
            treatment_qs = treatment_qs.filter(date__date__range=(start, end))

        # Treatment Room Income
        room_income = treatment_qs.aggregate(total=Sum('amount'))['total'] or 0

        # Income summary by payment method
        income_summary = {}
        for item in cash_qs.values('payment_method').annotate(total=Sum('amount')):
            method = item['payment_method']
            income_summary[method] = income_summary.get(method, 0) + item['total']

        for item in treatment_qs.values('payment_method').annotate(total=Sum('amount')):
            method = item['payment_method']
            income_summary[method] = income_summary.get(method, 0) + item['total']

        income_summary_list = [{"payment_method": k, "total": v} for k, v in income_summary.items()]

        # Total Income and Outcome
        cash_total = cash_qs.aggregate(total=Sum('amount'))['total'] or 0
        total_income = cash_total + room_income
        total_outcome = outcome_qs.aggregate(total=Sum('amount'))['total'] or 0

        # Doctor income (from consultation)
        doctor_income = (
            cash_qs.filter(transaction_type='consultation')
            .select_related('doctor__user')
            .values('doctor__id', 'doctor__user__first_name', 'doctor__user__last_name')
            .annotate(total=Sum('amount'))
        )

        doctor_income_formatted = [
            {
                "doctor": {
                    "id": item['doctor__id'],
                    "first_name": item['doctor__user__first_name'],
                    "last_name": item['doctor__user__last_name'],
                },
                "total": float(item['total'])
            }
            for item in doctor_income
        ]

        # Service income breakdown
        service_income = []
        service_qs = cash_qs.filter(transaction_type='service')
        for s in service_qs:
            if s.notes and "Service Payment:" in s.notes:
                names = s.notes.replace("Service Payment:", "").split(",")
                for name in names:
                    clean = name.strip()
                    match = next((i for i in service_income if i["name"] == clean), None)
                    if match:
                        match["amount"] += s.amount
                    else:
                        service_income.append({"name": clean, "amount": s.amount})

        return Response({
            "total_income": float(total_income),
            "total_outcome": float(total_outcome),
            "balance": float(total_income - total_outcome),
            "incomes_by_method": income_summary_list,
            "doctor_income": doctor_income_formatted,
            "service_income": service_income,
            "room_income": float(room_income),
        })


class OutcomeListCreateView(generics.ListCreateAPIView):
    queryset = Outcome.objects.all().order_by('-created_at')
    serializer_class = OutcomeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        start = self.request.query_params.get('start_date')
        end = self.request.query_params.get('end_date')
        if start and end:
            qs = qs.filter(created_at__date__range=[start, end])
        return qs

class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "email": user.email,
            "is_superuser": user.is_superuser,
            "role": getattr(user, "role", None),
        })


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def profile_view(request):
#     user = request.user
#     return Response({
#         "id": user.id,
#         "email": user.email,
#         "role": getattr(user, "role", None),  # Optional: if you store role
#         "is_superuser": user.is_superuser,
#         "is_staff": user.is_staff,
#         "full_name": user.get_full_name() if hasattr(user, "get_full_name") else "",
#     })

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import UserProfileSerializer , PatientArchiveSerializer

class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

class PrintTreatmentReceiptView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({"message": "Receipt printed"})

class LabRegistrationListCreateAPIView(ListCreateAPIView):
    queryset = LabRegistration.objects.select_related('patient', 'service', 'visit').all().order_by('-created_at')
    serializer_class = LabRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        patient_id = self.request.query_params.get('patient')
        if patient_id:
            return self.queryset.filter(patient_id=patient_id)
        return self.queryset


class LabRegistrationDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = LabRegistration.objects.all()
    serializer_class = LabRegistrationSerializer
    permission_classes = [IsAuthenticated]

class PublicDoctorServiceAPI(APIView):
    permission_classes = []  # NO authentication

    def get(self, request, doctor_id):
        lab_regs = LabRegistration.objects.filter(service__doctor_id=doctor_id).select_related('patient', 'visit', 'service')
        serializer = LabRegistrationSerializer(lab_regs, many=True)
        return Response(serializer.data)


class PatientArchiveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        patients = Patient.objects.select_related('patients_doctor__user').prefetch_related(
            'appointment_set', 'treatmentregistration_set__room', 'labregistration_set__service'
        ).all().order_by('-created_at')
        serializer = PatientArchiveSerializer(patients, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LabRegistrationListCreateAPIView(ListCreateAPIView):
    queryset = LabRegistration.objects.select_related('patient', 'service', 'visit').all().order_by('-created_at')
    serializer_class = LabRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        patient_id = self.request.query_params.get('patient')
        if patient_id:
            return self.queryset.filter(patient_id=patient_id)
        return self.queryset

    def perform_create(self, serializer):
        try:
            request_data = self.request.data
            logger.info(f"Attempting to create LabRegistration with data: {request_data}")
            instance = serializer.save(created_by=self.request.user)
            logger.info(f"Lab registration created: patient={instance.patient.id}, visit={instance.visit.id}, service={instance.service.id}")
            return Response(serializer.data, status=HTTP_201_CREATED)
        except ValidationError as ve:
            logger.error(f"Validation error: {str(ve.detail if hasattr(ve, 'detail') else str(ve))}")
            return Response({"error": str(ve.detail if hasattr(ve, 'detail') else str(ve))}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating LabRegistration: {str(e)}", exc_info=True)
            return Response({"error": "An unexpected error occurred while creating the lab registration"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from .serializers import RoomHistorySerializer

class RoomHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        registrations = TreatmentRegistration.objects.select_related('room').all()
        serializer = RoomHistorySerializer(registrations, many=True)
        return Response(serializer.data)
