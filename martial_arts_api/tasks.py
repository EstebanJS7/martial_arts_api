from celery import shared_task
from datetime import date
from users.models import CustomUser, UserProfile
from payments.services import PaymentService

@shared_task
def generate_annual_payments_for_all_students():
    today = date.today()
    # Solo ejecuta si es enero (puedes ajustar el día si lo deseas)
    if today.month == 1:
        students = CustomUser.objects.filter(userprofile__role='student', userprofile__is_exempt=False)
        for user in students:
            PaymentService.create_payments_for_remaining_year(user)
        print(f"Cuotas anuales generadas para {students.count()} estudiantes no exentos.")

# (opcional) Mantén la tarea mensual si la quieres para otros propósitos
@shared_task
def generate_monthly_payments():
    today = date.today()
    if today.day == 1:
        from payments.models import QuotaConfig, Payment
        current_quota = QuotaConfig.objects.latest('id')
        users = CustomUser.objects.filter(userprofile__is_exempt=False)
        for user in users:
            Payment.objects.create(
                user=user,
                amount=current_quota.amount,
                due_date=current_quota.due_day
            )
