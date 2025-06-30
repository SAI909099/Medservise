from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_verification_email(email, verification_code):
    subject = "Verify Your Email"
    message = f"Your verification code is: {verification_code}"
    from_email = "no-reply@volumenzeit.com"
    recipient_list = [email]

    send_mail(subject, message, from_email, recipient_list)
    return f"Verification email sent to {email}"


from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from apps.models import Patient
import pandas as pd
from django.core.mail import EmailMessage
import os

@shared_task
def archive_old_patients_task():
    one_year_ago = timezone.now() - timedelta(days=365)
    patients = Patient.objects.filter(created_at__lte=one_year_ago)

    if not patients.exists():
        print("✅ No patients to archive.")
        return "No patients to archive"

    df = pd.DataFrame.from_records(
        patients.values('first_name', 'last_name', 'phone', 'address', 'created_at')
    )

    # Fix timezone-aware datetime
    df["created_at"] = df["created_at"].apply(lambda dt: dt.replace(tzinfo=None))

    filename = f"patients_archive_{timezone.now().strftime('%Y-%m')}.xlsx"
    filepath = os.path.join("/tmp", filename)
    df.to_excel(filepath, index=False)

    # Send email
    email = EmailMessage(
        subject="📁 Monthly Patient Archive",
        body="Attached is the archive of patients registered over 1 year ago.",
        from_email="sulaymonovabdulaziz1@gmail.com",
        to=["sulaymonovabdulaziz1@gmail.com"],
    )
    email.attach_file(filepath)
    email.send()

    # Delete patients after archiving
    patients.delete()

    return f"{len(df)} patients archived and emailed."



@shared_task
def apply_daily_room_charges():
    from apps.models import TreatmentRegistration

    for reg in TreatmentRegistration.objects.filter(discharged_at__isnull=True):
        price = reg.room.price_per_day
        reg.total_paid += price
        reg.save()