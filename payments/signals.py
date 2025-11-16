from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.services import create_and_notify
from .models import Payment, PaymentTransaction


@receiver(post_save, sender=Payment)
def payment_created_or_updated(sender, instance: Payment, created: bool, **kwargs):
    user_id = instance.user_id
    if created:
        create_and_notify(
            recipient_id=user_id,
            title='Nuevo pago generado',
            message=f'Se generó un pago por {instance.amount} con vencimiento {instance.due_date:%d/%m/%Y}',
            ntype='payment',
            payload={'payment_id': instance.id, 'due_date': str(instance.due_date), 'amount': str(instance.amount)},
        )
    else:
        if instance.is_paid or instance.is_fully_paid:
            create_and_notify(
                recipient_id=user_id,
                title='Pago recibido',
                message=f'Tu pago de {instance.amount_paid} fue acreditado',
                ntype='payment',
                payload={'payment_id': instance.id, 'amount_paid': str(instance.amount_paid)},
            )


@receiver(post_save, sender=PaymentTransaction)
def payment_transaction_created(sender, instance: PaymentTransaction, created: bool, **kwargs):
    if not created:
        return
    payment = instance.payment
    create_and_notify(
        recipient_id=payment.user_id,
        title='Transacción registrada',
        message=f'Se registró una transacción por {instance.amount}',
        ntype='payment',
        payload={'payment_id': payment.id, 'transaction_id': instance.id, 'amount': str(instance.amount)},
    )








