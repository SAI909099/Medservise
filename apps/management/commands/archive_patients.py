from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from django.utils import timezone
from apps.models import Patient
from datetime import datetime, timedelta
import pandas as pd
import os


class Command(BaseCommand):
    help = 'Archive patients older than 1 year, email to admin, and delete them'

    def handle(self, *args, **kwargs):
        one_year_ago = timezone.now() - timedelta(days=365)
        patients = Patient.objects.filter(created_at__lt=one_year_ago)

        if not patients.exists():
            self.stdout.write("✅ No patients to archive.")
            return

        # Create export folder
        os.makedirs("archives", exist_ok=True)
        file_name = f"patients_archive_{datetime.now().strftime('%Y_%m')}.xlsx"
        file_path = os.path.join("archives", file_name)

        data = [{
            "First Name": p.first_name,
            "Last Name": p.last_name,
            "Phone": p.phone,
            "Address": p.address,
            "Created At": p.created_at
        } for p in patients]

        df = pd.DataFrame(data)
        df.to_excel(file_path, index=False)

        # Email
        email = EmailMessage(
            subject="🗂️ Archived Patients Export",
            body="Attached is the monthly archive of patients registered over a year ago.",
            from_email="your_email@gmail.com",
            to=["admin@example.com"]
        )
        email.attach_file(file_path)
        email.send()

        # Delete
        count = patients.count()
        patients.delete()
        self.stdout.write(f"✅ Archived and deleted {count} patients.")
