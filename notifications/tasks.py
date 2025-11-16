"""
Tareas de Celery para notificaciones.
"""
from celery import shared_task
from notifications.notification_scheduler import NotificationScheduler


@shared_task(name='notifications.tasks.send_class_reminders_task')
def send_class_reminders_task():
    """
    Tarea de Celery para enviar todos los recordatorios de clases.
    Se ejecuta cada 15 minutos mediante Celery Beat.
    """
    try:
        results = NotificationScheduler.process_all_reminders()
        return {
            'success': True,
            'results': results,
        }
    except Exception as e:
        # Log del error (en producción usar logging)
        print(f'Error al enviar recordatorios: {str(e)}')
        return {
            'success': False,
            'error': str(e),
        }


@shared_task(name='notifications.tasks.send_24h_reminders')
def send_24h_reminders():
    """
    Tarea de Celery para enviar recordatorios de 24 horas.
    """
    try:
        count = NotificationScheduler.send_class_reminders_24h()
        return {
            'success': True,
            'count': count,
        }
    except Exception as e:
        print(f'Error al enviar recordatorios de 24h: {str(e)}')
        return {
            'success': False,
            'error': str(e),
        }


@shared_task(name='notifications.tasks.send_1h_reminders')
def send_1h_reminders():
    """
    Tarea de Celery para enviar recordatorios de 1 hora.
    """
    try:
        count = NotificationScheduler.send_class_reminders_1h()
        return {
            'success': True,
            'count': count,
        }
    except Exception as e:
        print(f'Error al enviar recordatorios de 1h: {str(e)}')
        return {
            'success': False,
            'error': str(e),
        }


@shared_task(name='notifications.tasks.send_attendance_reminders')
def send_attendance_reminders():
    """
    Tarea de Celery para enviar recordatorios de asistencia.
    """
    try:
        count = NotificationScheduler.send_attendance_reminders()
        return {
            'success': True,
            'count': count,
        }
    except Exception as e:
        print(f'Error al enviar recordatorios de asistencia: {str(e)}')
        return {
            'success': False,
            'error': str(e),
        }

