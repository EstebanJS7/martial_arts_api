"""
Servicio para programar y enviar notificaciones inteligentes sobre clases.
"""
from django.utils import timezone
from datetime import timedelta
from classes.models import Class, UserClassReservation, ClassWaitlist
from .services import create_and_notify


class NotificationScheduler:
    """
    Servicio para enviar notificaciones programadas sobre clases.
    """
    
    @staticmethod
    def send_class_reminders_24h():
        """
        Envía recordatorios 24 horas antes de las clases.
        """
        now = timezone.now()
        # Buscar clases que empiecen entre 23.5 y 24.5 horas desde ahora
        target_time_start = now + timedelta(hours=23, minutes=30)
        target_time_end = now + timedelta(hours=24, minutes=30)
        
        upcoming_classes = Class.objects.filter(
            date__gte=target_time_start,
            date__lte=target_time_end,
            is_cancelled=False
        )
        
        notifications_sent = 0
        for class_obj in upcoming_classes:
            # Obtener todas las reservas activas para esta clase
            reservations = UserClassReservation.objects.filter(
                class_reserved=class_obj,
                is_cancelled=False
            )
            
            for reservation in reservations:
                # Verificar si ya se envió este recordatorio (evitar duplicados)
                # Podríamos usar un campo en el modelo o verificar notificaciones existentes
                # Por ahora, simplemente enviamos la notificación
                create_and_notify(
                    recipient_id=reservation.user_id,
                    title='Recordatorio: Clase mañana',
                    message=f'Recordatorio: Tienes una clase de {class_obj.name} mañana a las {class_obj.date:%H:%M}. ¡No olvides asistir!',
                    ntype='class',
                    payload={
                        'class_id': class_obj.id,
                        'reservation_id': reservation.id,
                        'reminder_type': '24h',
                        'class_date': class_obj.date.isoformat(),
                    },
                )
                notifications_sent += 1
        
        return notifications_sent
    
    @staticmethod
    def send_class_reminders_1h():
        """
        Envía recordatorios 1 hora antes de las clases.
        """
        now = timezone.now()
        # Buscar clases que empiecen entre 0.5 y 1.5 horas desde ahora
        target_time_start = now + timedelta(minutes=30)
        target_time_end = now + timedelta(hours=1, minutes=30)
        
        upcoming_classes = Class.objects.filter(
            date__gte=target_time_start,
            date__lte=target_time_end,
            is_cancelled=False
        )
        
        notifications_sent = 0
        for class_obj in upcoming_classes:
            # Obtener todas las reservas activas para esta clase
            reservations = UserClassReservation.objects.filter(
                class_reserved=class_obj,
                is_cancelled=False
            )
            
            for reservation in reservations:
                create_and_notify(
                    recipient_id=reservation.user_id,
                    title='¡Clase en 1 hora!',
                    message=f'Tu clase de {class_obj.name} comienza en 1 hora ({class_obj.date:%H:%M}). ¡Prepárate!',
                    ntype='class',
                    payload={
                        'class_id': class_obj.id,
                        'reservation_id': reservation.id,
                        'reminder_type': '1h',
                        'class_date': class_obj.date.isoformat(),
                    },
                )
                notifications_sent += 1
        
        return notifications_sent
    
    @staticmethod
    def send_class_cancellation_notifications(class_obj: Class, cancellation_reason: str = ''):
        """
        Envía notificaciones a todos los usuarios con reserva cuando se cancela una clase.
        """
        if not class_obj.is_cancelled:
            return 0
        
        reservations = UserClassReservation.objects.filter(
            class_reserved=class_obj,
            is_cancelled=False
        )
        
        notifications_sent = 0
        reason_text = f' Razón: {cancellation_reason}' if cancellation_reason else ''
        
        for reservation in reservations:
            create_and_notify(
                recipient_id=reservation.user_id,
                title='Clase cancelada',
                message=f'La clase {class_obj.name} programada para el {class_obj.date:%d/%m/%Y %H:%M} ha sido cancelada.{reason_text}',
                ntype='class',
                payload={
                    'class_id': class_obj.id,
                    'reservation_id': reservation.id,
                    'status': 'class_cancelled',
                    'cancellation_reason': cancellation_reason,
                },
            )
            notifications_sent += 1
        
        # También notificar a las personas en lista de espera
        waitlist_entries = ClassWaitlist.objects.filter(
            class_reserved=class_obj,
            status__in=['waiting', 'notified']
        )
        
        for waitlist_entry in waitlist_entries:
            create_and_notify(
                recipient_id=waitlist_entry.user_id,
                title='Clase cancelada',
                message=f'La clase {class_obj.name} para la cual estabas en lista de espera ha sido cancelada.{reason_text}',
                ntype='class',
                payload={
                    'class_id': class_obj.id,
                    'waitlist_id': waitlist_entry.id,
                    'status': 'class_cancelled',
                    'cancellation_reason': cancellation_reason,
                },
            )
            notifications_sent += 1
        
        return notifications_sent
    
    @staticmethod
    def send_attendance_reminders():
        """
        Envía recordatorios de asistencia después de que termine una clase.
        Esto puede ser útil para recordar a los instructores que marquen asistencia.
        """
        now = timezone.now()
        # Buscar clases que terminaron hace menos de 1 hora
        # (asumiendo que la duración promedio es de 1 hora)
        one_hour_ago = now - timedelta(hours=1)
        two_hours_ago = now - timedelta(hours=2)
        
        recent_classes = Class.objects.filter(
            date__gte=two_hours_ago,
            date__lte=one_hour_ago,
            is_cancelled=False
        )
        
        notifications_sent = 0
        for class_obj in recent_classes:
            # Solo notificar al instructor si hay reservas y aún no se ha marcado asistencia para todas
            if class_obj.instructor_id and class_obj.reservation_count > 0:
                # Verificar si hay reservas sin asistencia marcada
                reservations = UserClassReservation.objects.filter(
                    class_reserved=class_obj,
                    is_cancelled=False
                )
                
                # Contar cuántas tienen asistencia marcada
                from classes.models import ClassAttendance
                attendance_count = ClassAttendance.objects.filter(
                    class_reserved=class_obj
                ).count()
                
                # Si hay reservas sin asistencia marcada, notificar al instructor
                if attendance_count < reservations.count():
                    create_and_notify(
                        recipient_id=class_obj.instructor_id,
                        title='Recordatorio: Marcar asistencia',
                        message=f'Recuerda marcar la asistencia para la clase {class_obj.name} que terminó recientemente.',
                        ntype='class',
                        payload={
                            'class_id': class_obj.id,
                            'action': 'mark_attendance',
                            'reservations_count': reservations.count(),
                            'attendance_count': attendance_count,
                        },
                    )
                    notifications_sent += 1
        
        return notifications_sent
    
    @staticmethod
    def send_waitlist_position_updates():
        """
        Envía actualizaciones sobre cambios en la posición de la lista de espera.
        Esto se puede llamar cuando alguien se une o sale de la lista de espera.
        """
        # Esta función puede ser llamada desde los signals cuando cambia la lista de espera
        # Por ahora, solo la estructura básica
        pass
    
    @staticmethod
    def process_all_reminders():
        """
        Procesa todos los recordatorios pendientes.
        Esta función debe ser llamada periódicamente (cada 15-30 minutos).
        """
        results = {
            '24h_reminders': NotificationScheduler.send_class_reminders_24h(),
            '1h_reminders': NotificationScheduler.send_class_reminders_1h(),
            'attendance_reminders': NotificationScheduler.send_attendance_reminders(),
        }
        return results


