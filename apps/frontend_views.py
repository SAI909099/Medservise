# apps/users/frontend_views.py
from django.shortcuts import redirect, render
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views.generic import TemplateView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class IndexView(TemplateView):
    template_name = "index.html"

class AdminDashboardView(TemplateView):
    template_name = "admin-dashboard.html"

class ArchiveView(TemplateView):
    template_name = "archive.html"

class CashRegisterView(TemplateView):
    template_name = "cash-register.html"

class DoctorView(TemplateView):
    template_name = "doctor.html"

class DoctorAddView(TemplateView):
    template_name = "doctor-add.html"

class DoctorPatientRoomsView(TemplateView):
    template_name = "doctor-patient-rooms.html"

class DoctorPaymentsView(TemplateView):
    template_name = "doctor-payments.html"

class PatientDetailView(TemplateView):
    template_name = "patient-detail.html"

class PatientSelectionView(TemplateView):
    template_name = "patient_selection.html"

class PatientsView(TemplateView):
    template_name = "patients.html"

class PaymentsView(TemplateView):
    template_name = "payments.html"

class PriceManagementView(TemplateView):
    template_name = "price-management.html"

class RegisterView(TemplateView):
    template_name = "register.html"

class RegistrationView(TemplateView):
    template_name = "registration.html"

class RoomsView(TemplateView):
    template_name = "rooms.html"

class ServicesView(TemplateView):
    template_name = "services.html"

class TreatmentView(TemplateView):
    template_name = "treatment.html"

class TreatmentRegistrationView(TemplateView):
    template_name = "treatment-registration.html"

class TreatmentRoomManagementView(TemplateView):
    template_name = "treatment-room-management.html"

class TreatmentRoomPaymentsView(TemplateView):
    template_name = "treatment-room-payments.html"

class TurnDisplayView(TemplateView):
    template_name = "turn-display.html"

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_superuser": user.is_superuser,
        })