
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')

app = Celery('root')  # Replace 'your_project' with your project's name.

# Configure Celery using settings from Django settings.py.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load tasks from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

app.conf.broker_connection_retry_on_startup = True

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'archive-old-patients-monthly': {
        'task': 'apps.tasks.archive_old_patients_task',
        'schedule': crontab(day_of_month=1, hour=2, minute=0),  # 🗓 Monthly
    },
    'daily-room-charges': {
        'task': 'apps.tasks.apply_daily_room_charges',
        'schedule': crontab(minute='*'),  # 🕘 Daily at 9 AM
    },
}
