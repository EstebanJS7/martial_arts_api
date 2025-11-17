"""
Tareas de Celery para pagos.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta, date
from .models import Payment
from notifications.services import create_and_notify


@shared_task(name='payments.tasks.generate_monthly_payments_task')
def generate_monthly_payments_task():
    """
    Genera automáticamente las cuotas mensuales para todos los usuarios no exentos.
    Se ejecuta el día 1 de cada mes.
    """
    today = date.today()
    
    # Solo ejecutar el día 1 de cada mes
    if today.day != 1:
        return {
            'success': False,
            'message': 'Esta tarea solo se ejecuta el día 1 de cada mes',
            'current_day': today.day,
        }
    
    try:
        from payments.models import QuotaConfig
        from users.models import CustomUser
        
        # Obtener la configuración de cuota actual
        current_quota = QuotaConfig.objects.latest('id')
        
        # Obtener todos los usuarios no exentos
        users = CustomUser.objects.filter(userprofile__is_exempt=False)
        
        payments_created = 0
        for user in users:
            # Verificar si ya existe un pago para este mes
            existing_payment = Payment.objects.filter(
                user=user,
                due_date__year=today.year,
                due_date__month=today.month,
                is_fully_paid=False
            ).first()
            
            # Solo crear si no existe
            if not existing_payment:
                Payment.objects.create(
                    user=user,
                    amount=current_quota.amount,
                    due_date=date(today.year, today.month, current_quota.due_day)
                )
                payments_created += 1
        
        return {
            'success': True,
            'payments_created': payments_created,
            'total_users': users.count(),
            'month': today.month,
            'year': today.year,
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
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


@shared_task(name='payments.tasks.notify_upcoming_payments')
def notify_upcoming_payments():
    """
    Notifica a los usuarios sobre pagos próximos a vencer (3 días antes).
    Se ejecuta diariamente.
    """
    today = timezone.now().date()
    three_days_from_now = today + timedelta(days=3)
    
    # Buscar pagos que vencen en los próximos 3 días
    upcoming_payments = Payment.objects.filter(
        due_date__gte=today,
        due_date__lte=three_days_from_now,
        is_fully_paid=False
    ).select_related('user')
    
    notifications_sent = 0
    for payment in upcoming_payments:
        days_until_due = (payment.due_date - today).days
        
        create_and_notify(
            recipient_id=payment.user_id,
            title='Pago próximo a vencer',
            message=f'Tienes un pago de ${payment.amount} que vence en {days_until_due} día(s) ({payment.due_date:%d/%m/%Y})',
            ntype='payment',
            payload={
                'payment_id': payment.id,
                'amount': str(payment.amount),
                'due_date': str(payment.due_date),
                'days_until_due': days_until_due,
                'status': 'upcoming',
            },
        )
        notifications_sent += 1
    
    return {
        'success': True,
        'notifications_sent': notifications_sent,
        'upcoming_payments_count': upcoming_payments.count(),
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
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        ).count()
        
        paid_payments = Payment.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end,
            is_fully_paid=True
        ).count()
        
        overdue_payments = Payment.objects.filter(
            due_date__lt=today,
            is_fully_paid=False
        ).count()
        
        total_collected = sum(
            payment.amount_paid 
            for payment in Payment.objects.filter(
                created_at__date__gte=month_start,
                created_at__date__lte=month_end,
                is_fully_paid=True
            )
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


