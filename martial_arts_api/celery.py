from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Establece el módulo de configuración de Django al proyecto correcto.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'martial_arts_api.settings')

# Se crea la instancia de Celery utilizando el nombre del proyecto.
app = Celery('martial_arts_api')

# Lee la configuración desde settings.py con el namespace 'CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descubre y registra automáticamente las tareas definidas en las apps de Django.
app.autodiscover_tasks()