from datetime import date
from .models import Payment, CurrentQuota

def create_next_month_payment(user):
    """
    Crea automáticamente un pago para el próximo mes si no existe ya un pago para esa fecha.
    
    Args:
        user (User): El usuario para quien se está creando el pago.
    """
    current_date = date.today()
    next_month = current_date.month + 1 if current_date.month < 12 else 1
    next_year = current_date.year if current_date.month < 12 else current_date.year + 1
    next_due_date = date(next_year, next_month, 10)

    # Obtener la cuota actual
    current_quota = CurrentQuota.objects.latest('effective_date')

    # Crear un pago solo si no existe uno para la próxima fecha de vencimiento
    if not Payment.objects.filter(user=user, due_date=next_due_date).exists():
        Payment.objects.create(
            user=user,
            amount=current_quota.amount,  # Usar el monto de la cuota actual
            due_date=next_due_date,
            description="Pago mensual"
        )
