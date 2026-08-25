from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from notifications.services import create_and_notify
from notifications.notification_scheduler import NotificationScheduler
from .models import UserClassReservation, ClassAttendance, Class, ClassWaitlist


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
            
            # Verificar si hay personas en la lista de espera y notificar a la primera
            _notify_waitlist_availability(cls)


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
    """Actualizar cancelled_at cuando se cancela una clase y guardar valores anteriores"""
    if instance.pk:
        try:
            old_instance = Class.objects.get(pk=instance.pk)
            # Guardar el valor anterior de reservation_count para usarlo en post_save
            instance._old_reservation_count = old_instance.reservation_count
            instance._old_is_cancelled = old_instance.is_cancelled
            
            # Si cambió de no cancelada a cancelada
            if not old_instance.is_cancelled and instance.is_cancelled:
                instance.cancelled_at = timezone.now()
                # Guardar la razón de cancelación para usarla en el post_save
                instance._cancellation_reason = instance.cancellation_reason or ''
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
        instance._cancellation_reason = instance.cancellation_reason or ''


@receiver(post_save, sender=Class)
def class_reservation_count_changed(sender, instance: Class, **kwargs):
    """
    Cuando cambia el número de reservas de una clase, verificar si hay cupos disponibles
    para notificar a las personas en la lista de espera.
    También envía notificaciones cuando se cancela una clase.
    """
    if instance.pk:
        try:
            # Refrescar el objeto desde la base de datos para obtener valores actualizados
            # (necesario cuando se usa F() para actualizar campos)
            instance.refresh_from_db()
            
            # Obtener el valor anterior guardado en pre_save
            old_count = getattr(instance, '_old_reservation_count', None)
            old_is_cancelled = getattr(instance, '_old_is_cancelled', False)
            new_count = instance.reservation_count
            
            # Si el número de reservas disminuyó (se canceló una reserva)
            # Verificar que ambos valores sean enteros antes de comparar
            if old_count is not None and isinstance(old_count, int) and isinstance(new_count, int):
                if old_count > new_count:
                    _notify_waitlist_availability(instance)
            
            # Si la clase fue cancelada, notificar a todos los usuarios con reserva
            if not old_is_cancelled and instance.is_cancelled:
                cancellation_reason = getattr(instance, '_cancellation_reason', instance.cancellation_reason or '')
                NotificationScheduler.send_class_cancellation_notifications(instance, cancellation_reason)
        except Class.DoesNotExist:
            pass


@receiver(post_delete, sender=ClassWaitlist)
def waitlist_entry_deleted(sender, instance: ClassWaitlist, **kwargs):
    """
    Cuando se elimina físicamente una entrada de lista de espera,
    compacta las posiciones (1..N) de las entradas activas restantes.
    """
    class_obj_id = instance.class_reserved_id
    if class_obj_id is None:
        return
    class_obj = Class.objects.filter(pk=class_obj_id).first()
    if class_obj is not None:
        ClassWaitlist.compact_positions(class_obj)


def _notify_waitlist_availability(class_obj: Class):
    """
    Notifica a la primera persona en la lista de espera cuando hay un cupo disponible.
    """
    # Verificar que haya cupos disponibles
    if class_obj.reservation_count >= class_obj.max_students:
        return
    
    # Obtener la primera entrada en la lista de espera que esté en estado 'waiting'
    first_waitlist_entry = ClassWaitlist.objects.filter(
        class_reserved=class_obj,
        status='waiting'
    ).order_by('position', 'joined_at').first()
    
    if first_waitlist_entry:
        # Actualizar el estado a 'notified'
        first_waitlist_entry.status = 'notified'
        first_waitlist_entry.notified_at = timezone.now()
        first_waitlist_entry.save()
        
        # Notificar al usuario
        create_and_notify(
            recipient_id=first_waitlist_entry.user_id,
            title='¡Cupo disponible!',
            message=f'Hay un cupo disponible para {class_obj.name} el {class_obj.date:%d/%m/%Y %H:%M}. Tienes tiempo limitado para reservar.',
            ntype='class',
            payload={
                'class_id': class_obj.id,
                'waitlist_id': first_waitlist_entry.id,
                'position': first_waitlist_entry.position,
                'status': 'notified',
                'action': 'convert_to_reservation'
            },
        )







