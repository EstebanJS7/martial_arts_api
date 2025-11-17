from django.db import models
from django.conf import settings
from datetime import date

class QuotaConfig(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_day = models.IntegerField(default=10)  # Día de vencimiento de cada mes
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Si esta configuración se está marcando como activa,
        # desactivar todas las demás configuraciones
        if self.is_active:
            QuotaConfig.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_config(cls):
        """Obtiene la configuración de cuota activa actual"""
        try:
            return cls.objects.get(is_active=True)
        except cls.DoesNotExist:
            return None

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
        # Obtener la configuración de cuota activa actual
        current_quota = QuotaConfig.get_active_config()
        if current_quota:
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

    class Meta:
        indexes = [
            models.Index(fields=['user', 'due_date']),  # Para consultas de pagos por usuario y fecha
            models.Index(fields=['due_date', 'is_fully_paid']),  # Para consultas de pagos vencidos
            models.Index(fields=['user', 'is_fully_paid']),  # Para consultas de estado de pago por usuario
            models.Index(fields=['due_date']),  # Para ordenar por fecha de vencimiento
            models.Index(fields=['is_paid', 'is_fully_paid']),  # Para filtrar por estado de pago
        ]

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

    class Meta:
        indexes = [
            models.Index(fields=['payment', 'transaction_date']),  # Para consultas de transacciones por pago
            models.Index(fields=['transaction_date']),  # Para ordenar por fecha de transacción
        ]

    def __str__(self):
        return f"Transacción de {self.amount} en {self.transaction_date}"


class PaymentStats(models.Model):
    """
    Estadísticas de pagos para el dashboard y reportes.
    """
    date = models.DateField(unique=True)
    total_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    overdue_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_count = models.IntegerField(default=0)
    collection_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name = "Estadística de Pago"
        verbose_name_plural = "Estadísticas de Pagos"

    @classmethod
    def get_monthly_stats(cls, year, month):
        """Obtiene estadísticas para un mes específico"""
        try:
            return cls.objects.get(date__year=year, date__month=month)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_dashboard_data(cls):
        """Obtiene datos para el dashboard principal"""
        from datetime import date, timedelta
        
        today = date.today()
        last_month = today.replace(day=1) - timedelta(days=1)
        
        # Estadísticas del mes actual
        current_month = cls.get_monthly_stats(today.year, today.month)
        
        # Estadísticas del mes anterior
        previous_month = cls.get_monthly_stats(last_month.year, last_month.month)
        
        # Tendencias de los últimos 6 meses
        six_months_ago = today.replace(day=1) - timedelta(days=150)
        trends = cls.objects.filter(
            date__gte=six_months_ago,
            date__lte=today
        ).order_by('date')
        
        return {
            'current_month': current_month,
            'previous_month': previous_month,
            'trends': trends,
            'period': f"{six_months_ago.strftime('%Y-%m')} a {today.strftime('%Y-%m')}"
        }

    def __str__(self):
        return f"Estadísticas de {self.date.strftime('%Y-%m')}"
