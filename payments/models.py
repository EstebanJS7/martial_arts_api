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
        # Completar la fecha de vencimiento si no se proporciona
        if not self.due_date:
            self.due_date = self._get_next_due_date(current_quota)
        # Asignar el monto si no se especifica
        if not self.amount:
            self.amount = current_quota.amount
        # Si se marca como pago completo, forzamos amount_paid al monto total
        if self.is_fully_paid:
            self.amount_paid = self.amount
            self.is_paid = True
        super().save(*args, **kwargs)

    def _get_next_due_date(self, current_quota):
        """Calcula la próxima fecha de vencimiento según la configuración de la cuota"""
        today = date.today()
        next_month = today.month + 1 if today.month < 12 else 1
        year = today.year if today.month < 12 else today.year + 1
        return date(year, next_month, current_quota.due_day)

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


class PaymentTransaction(models.Model):
    """
    Registro de cada transacción de pago para auditoría y seguimiento.
    """
    payment = models.ForeignKey(Payment, related_name="transactions", on_delete=models.CASCADE)
    transaction_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)
    # Información adicional para auditoría
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    external_transaction_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Transacción de {self.amount} en {self.transaction_date}"
