"""
Tareas de Celery para listas de espera de clases.
"""
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Class, ClassWaitlist
from .signals import _notify_waitlist_availability


@shared_task(name='classes.tasks.expire_stale_notified_waitlist_entries')
def expire_stale_notified_waitlist_entries():
    """
    Expira las entradas de lista de espera en estado 'notified' cuyo tiempo
    para convertir la notificación en reserva venció.

    La ventana configurable es WAITLIST_NOTIFIED_EXPIRY_HOURS (horas desde
    notified_at, por defecto 24). Al expirar:
      - status pasa a 'cancelled'
      - se compactan las posiciones (1..N) restantes de la clase
      - si el cupo sigue libre, se notifica al próximo usuario en espera

    Idempotente: solo afecta entradas que siguen en 'notified' con
    notified_at anterior al corte, por lo que ejecuciones repetidas o
    concurrentes no duplican efectos.
    """
    expiry_hours = int(getattr(settings, 'WAITLIST_NOTIFIED_EXPIRY_HOURS', 24))
    cutoff = timezone.now() - timedelta(hours=expiry_hours)

    # Clases afectadas (agrupadas para compactar/notificar una sola vez)
    affected_class_ids = (
        ClassWaitlist.objects.filter(
            status='notified',
            notified_at__lt=cutoff,
        )
        .values_list('class_reserved_id', flat=True)
        .distinct()
    )

    expired_count = 0
    processed_classes = 0

    for class_id in list(affected_class_ids):
        class_obj = Class.objects.filter(pk=class_id).first()
        if class_obj is None:
            continue

        with transaction.atomic():
            # El filtro por status='notified' hace la operación idempotente y
            # segura frente a conversiones concurrentes de la misma entrada.
            updated = ClassWaitlist.objects.filter(
                class_reserved_id=class_id,
                status='notified',
                notified_at__lt=cutoff,
            ).update(status='cancelled')

            if updated:
                expired_count += updated
                ClassWaitlist.compact_positions(class_obj)

        if updated:
            processed_classes += 1
            # Reutiliza el patrón existente: marca al próximo 'waiting' como
            # 'notified' solo si el cupo sigue libre.
            _notify_waitlist_availability(class_obj)

    return {
        'success': True,
        'expired_entries': expired_count,
        'processed_classes': processed_classes,
        'expiry_hours': expiry_hours,
    }
