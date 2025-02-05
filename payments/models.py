from django.db import models
from django.conf import settings
from datetime import date

class QuotaConfig(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_day = models.IntegerField(default=10)  # Día de vencimiento de cada mes

    def __str__(self):
        return f"Cuota de {self.amount} con vencimiento el día {self.due_day} de cada mes."

class Payment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date_payment = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    is_fully_paid = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Obtener la configuración de cuota más reciente
        current_quota = QuotaConfig.objects.latest('id')

        # Calcular automáticamente la fecha de vencimiento si no está definida
        if not self.due_date:
            self.due_date = self._get_next_due_date(current_quota)

        # Asignar el monto de la cuota actual si no se especifica
        if not self.amount:
            self.amount = current_quota.amount

        super().save(*args, **kwargs)

    @classmethod
    def create_payments_for_remaining_year(cls, user):
        """ Crea pagos automáticos hasta el final del año actual (o siguiente) """
        current_quota = QuotaConfig.objects.latest('id')
        today = date.today()
        # Si estamos después del día de vencimiento, iniciar desde el siguiente mes
        start_month = today.month if today.day <= current_quota.due_day else today.month + 1
        end_year = today.year

        payments = []
        for month in range(start_month, 13):
            due_date = date(end_year, month, current_quota.due_day)
            payment = cls(user=user, due_date=due_date, amount=current_quota.amount, is_paid=False)
            payments.append(payment)
        cls.objects.bulk_create(payments)

    def _get_next_due_date(self, current_quota):
        """ Calcula la próxima fecha de vencimiento según la cuota configurada """
        today = date.today()
        next_month = today.month + 1 if today.month < 12 else 1
        year = today.year if today.month < 12 else today.year + 1
        return date(year, next_month, current_quota.due_day)

    @staticmethod
    def apply_payment(user, payment_amount):
        """ Aplica un pago a los pagos pendientes del usuario """
        pending_payments = Payment.objects.filter(user=user, is_fully_paid=False).order_by('due_date')
        for payment in pending_payments:
            amount_needed = payment.amount - payment.amount_paid
            if payment_amount >= amount_needed:
                payment.amount_paid = payment.amount
                payment.is_fully_paid = True
                payment.is_paid = True
                payment_amount -= amount_needed
            else:
                payment.amount_paid += payment_amount
                payment_amount = 0
            payment.save()

    def __str__(self):
        today = date.today()
        if self.is_paid and self.is_fully_paid:
            return f"{self.user.email} - {self.amount} - Pagado"
        elif 0 < self.amount_paid < self.amount:
            return f"{self.user.email} - {self.amount_paid}/{self.amount} - Parcial"
        elif today > self.due_date:
            return f"{self.user.email} - {self.amount} - Vencido"
        else:
            return f"{self.user.email} - {self.amount} - Pendiente"

    def is_due(self):
        """ Verifica si el pago está vencido """
        return date.today() > self.due_date
