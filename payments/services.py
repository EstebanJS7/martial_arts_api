from decimal import Decimal
from datetime import date
from .models import Payment, QuotaConfig, PaymentTransaction

class PaymentService:
    @classmethod
    def apply_payment(cls, user, payment_amount, payment_method=None, description=None):
        payment_amount = Decimal(payment_amount)
        # Obtener pagos pendientes del usuario ordenados por fecha de vencimiento
        pending_payments = Payment.objects.filter(user=user, is_fully_paid=False).order_by('due_date')
        for payment in pending_payments:
            amount_needed = payment.amount - payment.amount_paid
            if payment_amount <= 0:
                break  # No queda monto para aplicar

            if payment_amount >= amount_needed:
                # Pago total para la cuota
                payment.amount_paid = payment.amount
                payment.is_paid = True
                payment.is_fully_paid = True
                PaymentTransaction.objects.create(
                    payment=payment,
                    amount=amount_needed,
                    description=description or "Pago completado",
                    payment_method=payment_method
                )
                payment_amount -= amount_needed
            else:
                # Pago parcial
                payment.amount_paid += payment_amount
                PaymentTransaction.objects.create(
                    payment=payment,
                    amount=payment_amount,
                    description=description or "Pago parcial",
                    payment_method=payment_method
                )
                payment_amount = Decimal(0)
                if payment.amount_paid == payment.amount:
                    payment.is_paid = True
                    payment.is_fully_paid = True

            payment.save()

        return payment_amount

    @classmethod
    def create_payments_for_remaining_year(cls, user):
        """
        Crea pagos automáticos para el usuario desde el mes actual (o el siguiente si ya pasó el día de vencimiento)
        hasta diciembre, usando la configuración de cuota más reciente.
        """
        try:
            current_quota = QuotaConfig.objects.latest('id')
        except QuotaConfig.DoesNotExist:
            # No se encontró configuración de cuota; se puede optar por lanzar una excepción o simplemente retornar.
            raise Exception("No se encontró una configuración de cuota.")
        
        today = date.today()
        # Si hoy ya pasó el día de vencimiento, comenzar desde el siguiente mes
        start_month = today.month if today.day <= current_quota.due_day else today.month + 1
        payments = []
        for month in range(start_month, 13):
            due_date = date(today.year, month, current_quota.due_day)
            payment = Payment.objects.create(
                user=user,
                amount=current_quota.amount,
                due_date=due_date
            )
            payments.append(payment)
        return payments
