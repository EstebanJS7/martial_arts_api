from django.db import models
from django.conf import settings
from datetime import date

class CurrentQuota(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Current Quota: {self.amount} effective from {self.effective_date}"

class Payment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_payment = models.DateTimeField(auto_now_add=True)  # Renombrado a date_payment
    description = models.CharField(max_length=255, blank=True, null=True)
    due_date = models.DateField(default=date.today)

    def save(self, *args, **kwargs):
        # Calcular automáticamente la fecha de vencimiento como el día 10 del próximo mes si no se especifica
        if not self.due_date:
            self.due_date = self._get_next_due_date()

        # Asigna el monto de la cuota actual si el monto no se especifica
        if not self.amount:
            current_quota = CurrentQuota.objects.latest('effective_date')
            self.amount = current_quota.amount

        super().save(*args, **kwargs)

    def _get_next_due_date(self):
        # Establecer la próxima fecha de vencimiento como el 10 del próximo mes
        today = date.today()
        next_month = today.month + 1 if today.month < 12 else 1
        year = today.year if today.month < 12 else today.year + 1
        return date(year, next_month, 10)

    @staticmethod
    def is_user_up_to_date(user):
        # Verifica si el usuario está al día con los pagos
        latest_payment = Payment.objects.filter(user=user).order_by('-due_date').first()
        if latest_payment:
            return latest_payment.due_date >= date.today()
        return False

    @staticmethod
    def get_user_advance_months(user):
        # Calcula cuántos meses por adelantado está un usuario
        latest_payment = Payment.objects.filter(user=user).order_by('-due_date').first()
        if latest_payment:
            months_ahead = (latest_payment.due_date.year - date.today().year) * 12 + latest_payment.due_date.month - date.today().month
            return max(0, months_ahead - 1)
        return 0

    def __str__(self):
        return f"{self.user.email} - {self.amount} - {'Due' if self.is_due() else 'Paid'}"

    def is_due(self):
        # Verifica si el pago está vencido
        return date.today() > self.due_date
