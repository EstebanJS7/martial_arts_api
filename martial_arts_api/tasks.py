from celery import shared_task
from datetime import date
from payments.models import Payment, CustomUser, QuotaConfig  # Se asume que en payments.models CustomUser es el modelo de usuario

@shared_task
def generate_monthly_payments():
    today = date.today()

    # Verificar si es el día 1 de un nuevo mes para generar los pagos del mes siguiente
    if today.day == 1:
        current_quota = QuotaConfig.objects.latest('id')
        # Filtramos a los usuarios que no estén exentos, accediendo al campo is_exempt del UserProfile
        users = CustomUser.objects.filter(userprofile__is_exempt=False)

        for user in users:
            Payment.objects.create(
                user=user,  # Se asocia el usuario directamente
                amount=current_quota.amount,
                due_date=current_quota.due_day  # Ajustar la lógica si es necesario
            )
