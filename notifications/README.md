# Sistema de Notificaciones Inteligentes

Este módulo implementa un sistema completo de notificaciones inteligentes para clases.

## Funcionalidades Implementadas

### 1. Recordatorios 24 horas antes
- Envía notificaciones a todos los usuarios con reserva 24 horas antes de que comience la clase
- Mensaje: "Recordatorio: Clase mañana"

### 2. Recordatorios 1 hora antes
- Envía notificaciones a todos los usuarios con reserva 1 hora antes de que comience la clase
- Mensaje: "¡Clase en 1 hora!"

### 3. Notificaciones de cancelación
- Se envían automáticamente cuando se cancela una clase
- Notifica a todos los usuarios con reserva activa
- Notifica a todos los usuarios en lista de espera
- Incluye la razón de cancelación si está disponible

### 4. Alertas de lista de espera
- Notifica automáticamente a la primera persona en la lista de espera cuando hay un cupo disponible
- Se activa cuando alguien cancela su reserva

### 5. Recordatorios de asistencia
- Notifica a los instructores después de que termine una clase para recordarles marcar asistencia
- Solo se envía si hay reservas sin asistencia marcada

### 6. Notificaciones Push/Web
- Sistema de notificaciones en tiempo real mediante WebSocket
- Soporte para notificaciones push del navegador
- Service Worker para notificaciones en segundo plano

## Configuración

### Ejecutar Recordatorios Manualmente

Para probar o ejecutar los recordatorios manualmente:

```bash
# Enviar todos los recordatorios
python manage.py send_class_reminders

# Enviar solo recordatorios de 24h
python manage.py send_class_reminders --reminder-type 24h

# Enviar solo recordatorios de 1h
python manage.py send_class_reminders --reminder-type 1h

# Enviar solo recordatorios de asistencia
python manage.py send_class_reminders --reminder-type attendance
```

### Configurar Ejecución Automática (Cron)

Para que los recordatorios se envíen automáticamente, configura un cron job que ejecute el comando cada 15-30 minutos:

#### Linux/Mac (crontab)

```bash
# Editar crontab
crontab -e

# Agregar estas líneas (ejecutar cada 15 minutos)
*/15 * * * * cd /ruta/a/martial_arts_api && source venv/bin/activate && python manage.py send_class_reminders >> /var/log/class_reminders.log 2>&1
```

#### Windows (Task Scheduler)

1. Abrir "Programador de tareas"
2. Crear tarea básica
3. Configurar para ejecutar cada 15 minutos
4. Acción: Iniciar programa
5. Programa: `python`
6. Argumentos: `manage.py send_class_reminders`
7. Iniciar en: `C:\ruta\a\martial_arts_api`

### Usando Celery (Opcional)

Si prefieres usar Celery para tareas programadas, puedes configurar Celery Beat:

```python
# En settings.py
CELERY_BEAT_SCHEDULE = {
    'send-class-reminders': {
        'task': 'notifications.tasks.send_class_reminders',
        'schedule': crontab(minute='*/15'),  # Cada 15 minutos
    },
}
```

## Estructura del Código

- `notification_scheduler.py`: Contiene la lógica para enviar todos los tipos de recordatorios
- `management/commands/send_class_reminders.py`: Comando Django para ejecutar recordatorios
- `services.py`: Servicio base para crear y enviar notificaciones
- `signals.py` (en classes): Integra las notificaciones con los eventos del sistema

## Notas Importantes

1. **Evitar Duplicados**: El sistema actual no previene duplicados automáticamente. Para producción, considera agregar un campo `reminder_sent_24h` y `reminder_sent_1h` en el modelo `UserClassReservation` para evitar enviar recordatorios múltiples veces.

2. **Zona Horaria**: Asegúrate de que la zona horaria de Django esté configurada correctamente en `settings.py`:
   ```python
   TIME_ZONE = 'America/Argentina/Buenos_Aires'  # Ajusta según tu ubicación
   ```

3. **Rendimiento**: Para sistemas con muchas clases, considera optimizar las consultas o usar Celery para procesar en segundo plano.

4. **Logs**: Los recordatorios se registran en la base de datos como notificaciones normales, pero también puedes agregar logging adicional si es necesario.

