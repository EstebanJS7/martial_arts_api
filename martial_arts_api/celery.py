from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

# Establece el módulo de configuración de Django para celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'martial_arts_api.settings')

app = Celery('martial_arts_api')

# Carga la configuración de Celery desde el archivo de configuración de Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubre tareas de todas las aplicaciones registradas en settings.py
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'generate-monthly-payments': {
        'task': 'payments.tasks.generate_payments_for_next_month',
        'schedule': crontab(minute=0, hour=0, day_of_month=1),  # Cada 1ro de mes a medianoche
    },
}