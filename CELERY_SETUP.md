# Configuración de Celery

Celery ha sido habilitado y configurado para automatizar las tareas de notificaciones.

## Configuración Realizada

### 1. Configuración de Celery en `settings.py`
- ✅ Broker URL: `redis://localhost:6379/0`
- ✅ Serializador: JSON
- ✅ Result Backend: Redis
- ✅ Timezone: Configurado según TIME_ZONE

### 2. Celery Beat Schedule
- ✅ **Recordatorios de clases**: Cada 15 minutos
- ✅ **Generación de cuotas anuales**: 1 de enero a las 00:00

### 3. Tareas Creadas
- ✅ `notifications.tasks.send_class_reminders_task`: Envía todos los recordatorios
- ✅ `notifications.tasks.send_24h_reminders`: Recordatorios de 24 horas
- ✅ `notifications.tasks.send_1h_reminders`: Recordatorios de 1 hora
- ✅ `notifications.tasks.send_attendance_reminders`: Recordatorios de asistencia

## Requisitos Previos

1. **Redis debe estar ejecutándose**:
   ```bash
   # Linux/Mac
   redis-server
   
   # Windows (usando Docker)
   docker run -d -p 6379:6379 redis:alpine
   
   # O instalar Redis para Windows
   ```

2. **Verificar que Redis esté funcionando**:
   ```bash
   redis-cli ping
   # Debe responder: PONG
   ```

## Cómo Iniciar Celery

### 1. Iniciar Worker de Celery
En una terminal separada:
```bash
cd martial_arts_api
celery -A martial_arts_api worker --loglevel=info
```

### 2. Iniciar Celery Beat (Scheduler)
En otra terminal separada:
```bash
cd martial_arts_api
celery -A martial_arts_api beat --loglevel=info
```

### 3. Iniciar ambos en una sola terminal (desarrollo)
```bash
cd martial_arts_api
celery -A martial_arts_api worker --beat --loglevel=info
```

## Verificar que Funciona

### Probar una tarea manualmente
```bash
# En el shell de Django
python manage.py shell

>>> from notifications.tasks import send_class_reminders_task
>>> result = send_class_reminders_task.delay()
>>> result.get()  # Ver el resultado
```

### Ver logs de Celery
Los logs mostrarán cuando se ejecutan las tareas programadas:
```
[2024-01-01 10:00:00,000: INFO/MainProcess] Task notifications.tasks.send_class_reminders_task[xxx] received
[2024-01-01 10:00:00,100: INFO/ForkPoolWorker-1] Enviados 5 recordatorios de 24 horas
[2024-01-01 10:00:00,200: INFO/ForkPoolWorker-1] Enviados 2 recordatorios de 1 hora
```

## Producción

Para producción, usa un proceso manager como `supervisor` o `systemd`:

### Supervisor (ejemplo)
```ini
[program:celery_worker]
command=/ruta/a/venv/bin/celery -A martial_arts_api worker --loglevel=info
directory=/ruta/a/martial_arts_api
user=www-data
autostart=true
autorestart=true

[program:celery_beat]
command=/ruta/a/venv/bin/celery -A martial_arts_api beat --loglevel=info
directory=/ruta/a/martial_arts_api
user=www-data
autostart=true
autorestart=true
```

## Troubleshooting

### Error: "Connection refused" (Redis)
- Verifica que Redis esté ejecutándose: `redis-cli ping`
- Verifica la URL en `CELERY_BROKER_URL`

### Error: "No module named 'celery'"
- Instala las dependencias: `pip install -r requirements.txt`

### Las tareas no se ejecutan
- Verifica que Celery Beat esté ejecutándose
- Verifica los logs de Celery Beat
- Verifica que Redis esté funcionando

### Cambiar frecuencia de recordatorios
Edita `CELERY_BEAT_SCHEDULE` en `settings.py`:
```python
'send-class-reminders': {
    'task': 'notifications.tasks.send_class_reminders_task',
    'schedule': crontab(minute='*/30'),  # Cada 30 minutos
},
```


