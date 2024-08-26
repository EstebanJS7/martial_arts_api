from celery import shared_task
from django.contrib.auth.models import User
from .utils import create_next_month_payment

@shared_task
def generate_payments_for_next_month():
    users = User.objects.all()
    for user in users:
        create_next_month_payment(user)