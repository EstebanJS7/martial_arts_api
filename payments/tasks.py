"""
Tareas de Celery para pagos.
"""
from celery import shared_task
from django.db import transaction as db_transaction
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
from .models import Payment, QuotaConfig
from notifications.services import create_and_notify


@shared_task(name='payments.tasks.generate_monthly_quotas')
def generate_monthly_quotas():
    """
    Genera las cuotas del mes en curso para todos los estudiantes activos
    (rol estudiante, usuario activo y no exentos), usando el monto y día de
    vencimiento de la configuración de cuota activa.

    Es idempotente por (usuario, período 'YYYY-MM'): si ya existe un pago para
    ese período se omite. Se programa el día 1 de cada mes a las 06:05.
    """
    try:
        from users.models import CustomUser

        current_quota = QuotaConfig.get_active_config()
        if not current_quota:
            return {
                'success': False,
                'message': 'No hay una configuración de cuota activa.',
            }

        today = timezone.now().date()
        period = f'{today.year}-{today.month:02d}'
        due_date = date(today.year, today.month, current_quota.due_day)

        students = CustomUser.objects.filter(
            is_active=True,
            userprofile__role='student',
            userprofile__is_exempt=False,
        )

        payments_created = 0
        with db_transaction.atomic():
            for student in students:
                # Idempotencia por (usuario, período): omitir si ya existe la cuota del mes
                _, created = Payment.objects.get_or_create(
                    user=student,
                    period=period,
                    defaults={
                        'amount': current_quota.amount,
                        'due_date': due_date,
                    },
                )
                if created:
                    payments_created += 1

        return {
            'success': True,
            'period': period,
            'payments_created': payments_created,
            'total_students': students.count(),
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


@shared_task(name='payments.tasks.mark_overdue_payments')
def mark_overdue_payments():
    """
    Marca como vencidos (is_overdue) los pagos cuya fecha de vencimiento ya pasó
    y que no están completamente pagados. También limpia la marca de pagos que
    quedaron al día o cuya fecha de vencimiento aún no llega.
    Se ejecuta diariamente antes de las notificaciones.
    """
    today = timezone.now().date()

    marked_count = Payment.objects.filter(
        is_fully_paid=False,
        due_date__lt=today,
    ).exclude(is_overdue=True).update(is_overdue=True)

    cleared_count = Payment.objects.filter(is_overdue=True).filter(
        Q(is_fully_paid=True) | Q(due_date__gte=today)
    ).update(is_overdue=False)

    return {
        'success': True,
        'marked_overdue': marked_count,
        'cleared_overdue': cleared_count,
    }


@shared_task(name='payments.tasks.remind_upcoming_due_payments')
def remind_upcoming_due_payments():
    """
    Notifica a los estudiantes cuya cuota vence exactamente en 3 días y que aún
    no la pagan completamente. Se ejecuta diariamente.
    """
    today = timezone.now().date()
    reminder_date = today + timedelta(days=3)

    upcoming_payments = Payment.objects.filter(
        due_date=reminder_date,
        is_fully_paid=False,
    ).select_related('user')

    notifications_sent = 0
    for payment in upcoming_payments:
        create_and_notify(
            recipient_id=payment.user_id,
            title='Recordatorio de pago próximo a vencer',
            message=f'Tu cuota de ${payment.amount} vence el {payment.due_date:%d/%m/%Y}. ¡No olvides realizar el pago!',
            ntype='payment',
            payload={
                'payment_id': payment.id,
                'amount': str(payment.amount),
                'due_date': str(payment.due_date),
                'status': 'upcoming',
            },
        )
        notifications_sent += 1

    return {
        'success': True,
        'notifications_sent': notifications_sent,
        'reminder_date': str(reminder_date),
    }


@shared_task(name='payments.tasks.notify_overdue_payments')
def notify_overdue_payments():
    """
    Notifica a los usuarios sobre pagos vencidos.
    Se ejecuta diariamente para verificar pagos vencidos.
    """
    today = timezone.now().date()
    
    # Buscar pagos vencidos que no estén completamente pagados
    overdue_payments = Payment.objects.filter(
        due_date__lt=today,
        is_fully_paid=False
    ).select_related('user')
    
    notifications_sent = 0
    for payment in overdue_payments:
        # Calcular días de vencimiento
        days_overdue = (today - payment.due_date).days
        
        # Solo notificar si no se ha notificado hoy (evitar spam)
        # En producción, podrías agregar un campo last_notified_date
        create_and_notify(
            recipient_id=payment.user_id,
            title='Pago vencido',
            message=f'Tienes un pago vencido de ${payment.amount} desde hace {days_overdue} día(s). Fecha de vencimiento: {payment.due_date:%d/%m/%Y}',
            ntype='payment',
            payload={
                'payment_id': payment.id,
                'amount': str(payment.amount),
                'due_date': str(payment.due_date),
                'days_overdue': days_overdue,
                'status': 'overdue',
            },
        )
        notifications_sent += 1
    
    return {
        'success': True,
        'notifications_sent': notifications_sent,
        'overdue_payments_count': overdue_payments.count(),
    }


@shared_task(name='payments.tasks.generate_monthly_report')
def generate_monthly_report():
    """
    Genera un reporte mensual de pagos y lo envía a los administradores.
    Se ejecuta el último día de cada mes.
    """
    today = date.today()
    
    # Verificar si es el último día del mes
    # (aproximación: día 28-31, verificar si el siguiente día es día 1)
    next_day = today + timedelta(days=1)
    if next_day.day != 1:
        return {
            'success': False,
            'message': 'Esta tarea solo se ejecuta el último día del mes',
            'current_day': today.day,
        }
    
    try:
        from users.models import CustomUser
        
        # Obtener todos los administradores
        admins = CustomUser.objects.filter(userprofile__role='admin')
        
        # Calcular estadísticas del mes
        month_start = date(today.year, today.month, 1)
        month_end = today
        
        total_payments = Payment.objects.filter(
            due_date__gte=month_start,
            due_date__lte=month_end
        ).count()

        paid_payments = Payment.objects.filter(
            due_date__gte=month_start,
            due_date__lte=month_end,
            is_fully_paid=True
        ).count()

        overdue_payments = Payment.objects.filter(
            due_date__lt=today,
            is_fully_paid=False
        ).count()

        total_collected = (
            Payment.objects.filter(
                due_date__gte=month_start,
                due_date__lte=month_end,
                is_fully_paid=True
            ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
        )
        
        # Enviar notificación a cada administrador
        notifications_sent = 0
        for admin in admins:
            create_and_notify(
                recipient_id=admin.id,
                title=f'Reporte mensual - {today.strftime("%B %Y")}',
                message=(
                    f'Reporte del mes de {today.strftime("%B %Y")}:\n'
                    f'• Total de pagos: {total_payments}\n'
                    f'• Pagos completados: {paid_payments}\n'
                    f'• Pagos vencidos: {overdue_payments}\n'
                    f'• Total recaudado: ${total_collected:.2f}'
                ),
                ntype='info',
                payload={
                    'report_type': 'monthly',
                    'month': today.month,
                    'year': today.year,
                    'total_payments': total_payments,
                    'paid_payments': paid_payments,
                    'overdue_payments': overdue_payments,
                    'total_collected': float(total_collected),
                },
            )
            notifications_sent += 1
        
        return {
            'success': True,
            'notifications_sent': notifications_sent,
            'month': today.month,
            'year': today.year,
            'stats': {
                'total_payments': total_payments,
                'paid_payments': paid_payments,
                'overdue_payments': overdue_payments,
                'total_collected': float(total_collected),
            },
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }



