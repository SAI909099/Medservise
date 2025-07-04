# ✅ FIXED urls.py
from django.urls import path
from apps.views import (
    # Auth
    RegisterAPIView, VerifyEmailAPIView, LoginAPIView, UserInfoListCreateAPIView,
    PasswordResetConfirmView, ActivateUserView,

    # Patients
    PatientRegistrationAPIView, PatientDetailAPIView, PatientListAPIView, RecentPatientsView, RecentPatientsByDaysView,

    # Doctors
    DoctorListCreateAPIView, DoctorRegistrationAPIView, CreateDoctorWithUserView, DoctorDetailView,

    # Appointments
    AppointmentListCreateAPIView, DoctorAppointmentListAPIView, DoctorAppointmentDetailAPIView,

    # Services
    ServiceListCreateAPIView, ServiceDetailAPIView,

    # Payments
    PaymentListCreateAPIView, TreatmentRoomPaymentsView, DoctorPaymentsAPIView, DoctorPaymentListView,

    # Treatment Rooms
    TreatmentRoomListCreateAPIView, TreatmentRoomDetailAPIView, TreatmentRoomList,
    AssignRoomAPIView, RoomStatusAPIView,

    # Treatment Registrations
    TreatmentRegistrationListCreateAPIView,

    # Patient Results
    PatientResultListCreateAPIView, PatientResultDetailAPIView,

    # Cash Register
    CashRegistrationListView, CashRegistrationView, CashRegisterReceiptView,
    CashRegisterListAPIView, CashRegisterListCreateAPIView, RecentPatientsAPIView
)

urlpatterns = [
    # --- Auth ---
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('verify-email/', VerifyEmailAPIView.as_view(), name='verify-email'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('reset-password/', PasswordResetConfirmView.as_view(), name='reset-password'),
    path('activate/<uidb64>/<token>', ActivateUserView.as_view(), name='activate'),

    # --- User Info ---
    path('user-detail/', UserInfoListCreateAPIView.as_view(), name='user-detail'),

    # --- Patients ---
    path('register-patient/', PatientRegistrationAPIView.as_view(), name='register-patient'),
    path('patients/', PatientListAPIView.as_view(), name='patient-list'),
    path('patients/<int:pk>/', PatientDetailAPIView.as_view(), name='patient-detail'),
    path('recent-patients/', RecentPatientsView.as_view(), name='recent-patients'),
    path('recent-patients-by-days/', RecentPatientsByDaysView.as_view(), name='recent-patients-by-days'),

    # --- Doctors ---
    path('doctor-list/', DoctorListCreateAPIView.as_view(), name='doctor-list'),
    path('doctor-list/<int:pk>/', DoctorDetailView.as_view(), name='doctor-detail'),
    path('doctor-register/', DoctorRegistrationAPIView.as_view(), name='doctor-register'),
    path('create-doctor/', CreateDoctorWithUserView.as_view(), name='create-doctor'),

    # --- Appointments ---
    path('appointment/', AppointmentListCreateAPIView.as_view(), name='appointment'),
    path('my-appointments/', DoctorAppointmentListAPIView.as_view(), name='doctor-appointments'),
    path('my-appointments/<int:pk>/', DoctorAppointmentDetailAPIView.as_view(), name='doctor-appointment-detail'),

    # --- Services ---
    path('services/', ServiceListCreateAPIView.as_view(), name='service-list-create'),
    path('services/<int:pk>/', ServiceDetailAPIView.as_view(), name='service-detail'),

    # --- Payments ---
    path('payment-list/', PaymentListCreateAPIView.as_view(), name='payment-list'),
    path('treatment-room-payments/', TreatmentRoomPaymentsView.as_view(), name='treatment-room-payments'),
    path('doctor-payments/', DoctorPaymentsAPIView.as_view(), name='doctor-payments-summary'),
    path('doctor-payments/list/', DoctorPaymentListView.as_view(), name='doctor-payments-list'),

    # --- Treatment Rooms ---
    path('treatment-rooms/', TreatmentRoomListCreateAPIView.as_view(), name='treatment-room-list-create'),
    path('treatment-rooms/list/', TreatmentRoomList.as_view(), name='treatment-room-list-only'),
    path('treatment-rooms/<int:pk>/', TreatmentRoomDetailAPIView.as_view(), name='treatment-room-detail'),
    path('room-status/', RoomStatusAPIView.as_view(), name='room-status'),
    path('assign-room/', AssignRoomAPIView.as_view(), name='assign-room'),
    path('assign-patient-to-room/', AssignRoomAPIView.as_view(), name='assign-room-alias'),

    # --- Treatment Registration ---
    path('treatment-register/', TreatmentRegistrationListCreateAPIView.as_view(), name='treatment-register'),

    # --- Patient Results ---
    path('patient-results/', PatientResultListCreateAPIView.as_view(), name='patient-result-list'),
    path('patient-results/<int:pk>/', PatientResultDetailAPIView.as_view(), name='patient-result-detail'),

    # --- Cash Register ---
    path('cash-registration/patients/', CashRegistrationListView.as_view(), name='cash-registration-patients'),
    path('cash-register/patient/<int:patient_id>/', CashRegistrationView.as_view(), name='cash-register-by-patient'),
    path('cash-register/receipt/<int:pk>/', CashRegisterReceiptView.as_view(), name='cash-register-receipt'),
    path('cash-register/', CashRegisterListCreateAPIView.as_view(), name='cash-register'),

    path('recent-patients/', RecentPatientsView.as_view(), name='recent-patients'),

]
