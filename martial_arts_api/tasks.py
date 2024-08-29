from celery import shared_task
from django.conf import settings
from .utils import create_next_month_payment

@shared_task
def generate_payments_for_next_month():
    users = settings.AUTH_USER_MODEL.objects.all()
    for user in users:
        create_next_month_payment(user)