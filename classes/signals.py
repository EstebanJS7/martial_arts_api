from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from notifications.services import create_and_notify
from .models import UserClassReservation, ClassAttendance, Class


@receiver(post_save, sender=UserClassReservation)
def reservation_created_or_updated(sender, instance: UserClassReservation, created: bool, **kwargs):
    cls = instance.class_reserved
    # Notificar al usuario sobre su reserva o cancelación
    if created and not instance.is_cancelled:
        create_and_notify(
            recipient_id=instance.user_id,
            title='Reserva confirmada',
            message=f'Te reservaste para {cls.name} el {cls.date:%d/%m/%Y %H:%M}',
            ntype='class',
            payload={'class_id': cls.id, 'reservation_id': instance.id, 'status': 'reserved'},
        )
        # Notificar instructor
        if cls.instructor_id:
            create_and_notify(
                recipient_id=cls.instructor_id,
                title='Nueva reserva en tu clase',
                message=f'{instance.user.email} se reservó para {cls.name}',
                ntype='class',
                payload={'class_id': cls.id, 'reservation_id': instance.id, 'user_id': instance.user_id},
            )
    else:
        # Actualización: si se cancela
        if instance.is_cancelled:
            create_and_notify(
                recipient_id=instance.user_id,
                title='Reserva cancelada',
                message=f'Tu reserva en {cls.name} fue cancelada',
                ntype='class',
                payload={'class_id': cls.id, 'reservation_id': instance.id, 'status': 'cancelled'},
            )
            if cls.instructor_id:
                create_and_notify(
                    recipient_id=cls.instructor_id,
                    title='Reserva cancelada',
                    message=f'{instance.user.email} canceló su reserva en {cls.name}',
                    ntype='class',
                    payload={'class_id': cls.id, 'reservation_id': instance.id, 'user_id': instance.user_id, 'status': 'cancelled'},
                )


@receiver(post_save, sender=ClassAttendance)
def attendance_marked(sender, instance: ClassAttendance, created: bool, **kwargs):
    cls = instance.class_reserved
    status = 'asistió' if instance.attended else 'no asistió'
    
    # Actualizar contadores de asistencia en la clase
    attendance_records = ClassAttendance.objects.filter(class_reserved=cls)
    cls.attendance_count = attendance_records.filter(attended=True).count()
    cls.no_show_count = attendance_records.filter(attended=False).count()
    cls.save(update_fields=['attendance_count', 'no_show_count'])
    
    # Notificar al usuario marcado
    create_and_notify(
        recipient_id=instance.user_id,
        title='Asistencia registrada',
        message=f'Se registró que {status} a {cls.name}',
        ntype='class',
        payload={'class_id': cls.id, 'attended': instance.attended, 'attendance_id': instance.id},
    )
    # Notificar instructor
    if cls.instructor_id:
        create_and_notify(
            recipient_id=cls.instructor_id,
            title='Asistencia actualizada',
            message=f'{instance.user.email} {status} a {cls.name}',
            ntype='class',
            payload={'class_id': cls.id, 'attended': instance.attended, 'attendance_id': instance.id, 'user_id': instance.user_id},
        )


@receiver(pre_save, sender=Class)
def class_pre_save(sender, instance: Class, **kwargs):
    """Actualizar cancelled_at cuando se cancela una clase"""
    if instance.pk:
        try:
            old_instance = Class.objects.get(pk=instance.pk)
            # Si cambió de no cancelada a cancelada
            if not old_instance.is_cancelled and instance.is_cancelled:
                instance.cancelled_at = timezone.now()
            # Si cambió de cancelada a no cancelada
            elif old_instance.is_cancelled and not instance.is_cancelled:
                instance.cancelled_at = None
                instance.cancellation_reason = ''
                instance.cancelled_by = None
        except Class.DoesNotExist:
            pass
    elif instance.is_cancelled:
        # Si es nueva y está cancelada desde el inicio
        instance.cancelled_at = timezone.now()







