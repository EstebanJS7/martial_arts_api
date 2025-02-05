from datetime import date, timedelta
from .models import Payment, QuotaConfig
from users.models import CustomUser

def create_next_month_payment(user):
    """
    Crea el pago para el próximo mes de un usuario.
    """
    current_quota = QuotaConfig.objects.latest('id')
    today = date.today()
    next_month = today.month + 1 if today.month < 12 else 1
    year = today.year if today.month < 12 else today.year + 1
    due_date = date(year, next_month, current_quota.due_day)
    payment = Payment.objects.create(
        user=user,
        amount=current_quota.amount,
        due_date=due_date
    )
    return payment

def check_user_due_status(user):
    """
    Verifica si el usuario tiene pagos vencidos.
    Se usan filtros directamente, ya que los métodos get_due_payments y get_upcoming_payments no están definidos.
    """
    due_payments = Payment.objects.filter(user=user, due_date__lt=date.today(), is_fully_paid=False)
    if due_payments.exists():
        return {
            'status': 'overdue',
            'due_payments': [p.id for p in due_payments]
        }
    else:
        upcoming_payment = Payment.objects.filter(user=user, due_date__gte=date.today(), is_fully_paid=False).order_by('due_date').first()
        return {
            'status': 'up_to_date',
            'next_payment_due_date': upcoming_payment.due_date if upcoming_payment else None
        }

def apply_user_payment(user, payment_amount):
    """
    Aplica el pago de un usuario a las deudas pendientes, comenzando por las más antiguas.
    """
    Payment.apply_payment(user, payment_amount)

def should_user_pay(user):
    """
    Verifica si el usuario debe pagar. Los usuarios con rol de administrador (definido en userprofile) no deben pagar.
    """
    return not (hasattr(user, 'userprofile') and user.userprofile.role == "admin")
