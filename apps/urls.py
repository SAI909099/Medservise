from django.urls import path

from apps.views import RegisterAPIView, VerifyEmailAPIView, LoginAPIView, UserInfoListCreateAPIView, \
    PasswordResetConfirmView, ActivateUserView, DoctorListCreateAPIView, \
    AppointmentListCreateAPIView, TreatmentRoomListCreateAPIView, TreatmentRegistrationListCreateAPIView, \
    PaymentListCreateAPIView, PatientRegistrationAPIView, DoctorAppointmentListAPIView, DoctorAppointmentDetailAPIView, \
    AssignPatientToRoomAPIView, AssignRoomAPIView, TreatmentRoomDetailAPIView, PatientResultListCreateAPIView, \
    PatientResultDetailAPIView, PatientDetailAPIView, PatientListAPIView, ServiceListCreateAPIView, \
    DoctorRegistrationAPIView, CreateDoctorWithUserView, DoctorDetailView, RoomStatusAPIView, TreatmentRoomList, \
    RecentPatientsView, ServiceDetailAPIView

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    # path('login/', LoginAPIView.as_view(), name='login'),
    path('verify-email/', VerifyEmailAPIView.as_view(), name='verify-email'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('user-detail/', UserInfoListCreateAPIView.as_view(), name='user-detail'),

    path('reset-password/', PasswordResetConfirmView.as_view(), name='reset-password'),

    path('activate/<uidb64>/<token>', ActivateUserView.as_view(), name='activate'),

    # //*/*/*/**/*///*/*/*/*/*/**//**//*/**/*/*/*/**//*/*/*/*/*/**//**/*//**/*/

    path('register-patient/', PatientRegistrationAPIView.as_view(), name='register_patient_api'),

    path('doctor-list/', DoctorListCreateAPIView.as_view(), name='Doctor-list'),
    path('appointment/', AppointmentListCreateAPIView.as_view(), name='appointment'),
    path('payment-list/', PaymentListCreateAPIView.as_view(), name='patient'),
    path('treatment-rooms/', TreatmentRoomListCreateAPIView.as_view()),
    path('treatment-register/', TreatmentRegistrationListCreateAPIView.as_view()),

    path('my-appointments/', DoctorAppointmentListAPIView.as_view(), name='doctor_appointments'),
    path('my-appointments/<int:pk>/', DoctorAppointmentDetailAPIView.as_view()),  # 👈 supports PATCH & DELETE

    path('doctor/appointments/<int:pk>/', DoctorAppointmentDetailAPIView.as_view(), name='doctor-appointment-detail'),

    path('assign-room/', AssignRoomAPIView.as_view(), name='assign-room'),
    path('assign-patient-room/', AssignPatientToRoomAPIView.as_view(), name='assign-patient-to-room'),

    path('treatment-rooms/', TreatmentRoomListCreateAPIView.as_view(), name='treatment-room-list'),
    path('treatment-rooms/<int:pk>/', TreatmentRoomDetailAPIView.as_view(), name='treatment-room-detail'),

    path('patients/<int:pk>/', PatientDetailAPIView.as_view(), name='patient-detail'),
    path('patient-detail/<int:pk>/', PatientDetailAPIView.as_view(), name='patient-detail'),


    path('patients/', PatientListAPIView.as_view(), name='patient-list'),
    path('patient-results/', PatientResultListCreateAPIView.as_view(), name='patient-result-list'),
    path('patient-results/<int:pk>/', PatientResultDetailAPIView.as_view(), name='patient-result-detail'),

    path('services/', ServiceListCreateAPIView.as_view(), name='service-list-create'),
    path('services/<int:pk>/', ServiceDetailAPIView.as_view(), name='service-detail'),

    path("doctor-register/", DoctorRegistrationAPIView.as_view(), name="doctor-register"),
    path("create-doctor/", CreateDoctorWithUserView.as_view(), name="create-doctor"),
    path('doctor-list/<int:pk>/', DoctorDetailView.as_view(), name='doctor-detail'),

    path('room-status/', RoomStatusAPIView.as_view(), name='room-status'),

    path('recent-patients/', RecentPatientsView.as_view(), name='recent-patients'),
    path('treatment-rooms/', TreatmentRoomList.as_view()),

    path('assign-patient-to-room/', AssignRoomAPIView.as_view(), name='assign-room'),

]
