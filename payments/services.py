from decimal import Decimal
from datetime import date, datetime, timedelta
from django.db.models import Sum, Count, Q
from .models import Payment, QuotaConfig, PaymentTransaction, PaymentStats

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


class PaymentDashboardService:
    """
    Servicio para generar estadísticas y datos del dashboard de pagos.
    """
    
    @classmethod
    def get_dashboard_overview(cls, period_months=1, user_email=None, start_date=None, end_date=None, payment_method=None):
        """
        Obtiene métricas principales para el dashboard con filtros opcionales
        
        Args:
            period_months: Período en meses para calcular métricas (default: 1 = mes actual)
            user_email: Filtrar por email de usuario (opcional)
            start_date: Fecha de inicio para filtrar (opcional)
            end_date: Fecha de fin para filtrar (opcional)
            payment_method: Método de pago para filtrar (opcional)
        """
        today = date.today()
        
        # Determinar rango de fechas basado en período
        if start_date and end_date:
            period_start = start_date
            period_end = end_date
        else:
            period_start = today.replace(day=1) - timedelta(days=(period_months - 1) * 30)
            period_end = today
        
        # Base queryset con filtros
        base_queryset = Payment.objects.all()
        
        # Filtrar por usuario si se especifica
        if user_email:
            base_queryset = base_queryset.filter(user__email__icontains=user_email)
        
        # Filtrar por rango de fechas (usando date_payment para recaudación y due_date para pendientes/vencidos)
        payments_in_period = base_queryset.filter(
            date_payment__gte=period_start,
            date_payment__lte=period_end
        )
        
        # Filtrar por método de pago si se especifica
        if payment_method:
            # Para recaudación, necesitamos filtrar por transacciones
            transaction_ids = PaymentTransaction.objects.filter(
                payment_method=payment_method
            ).values_list('payment_id', flat=True)
            payments_in_period = payments_in_period.filter(id__in=transaction_ids)
        
        # Métricas principales
        total_collected = payments_in_period.filter(
            is_fully_paid=True
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Pendientes y vencidos basados en due_date
        pending_query = base_queryset.filter(
            is_fully_paid=False,
            due_date__gte=today
        )
        if user_email:
            pending_query = pending_query.filter(user__email__icontains=user_email)
        
        pending_amount = pending_query.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        overdue_query = base_queryset.filter(
            is_fully_paid=False,
            due_date__lt=today
        )
        if user_email:
            overdue_query = overdue_query.filter(user__email__icontains=user_email)
        
        overdue_amount = overdue_query.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        payment_count = payments_in_period.count()
        
        # Tasa de recaudación
        total_expected = payments_in_period.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        collection_rate = (total_collected / total_expected * 100) if total_expected > 0 else Decimal('0')
        
        period_str = f"{period_start.strftime('%Y-%m')} a {period_end.strftime('%Y-%m')}" if period_months > 1 else period_start.strftime('%Y-%m')
        
        return {
            'total_collected': total_collected,
            'pending_amount': pending_amount,
            'overdue_amount': overdue_amount,
            'payment_count': payment_count,
            'collection_rate': collection_rate,
            'period': period_str
        }
    
    @classmethod
    def get_monthly_stats(cls, year, month):
        """Obtiene estadísticas detalladas para un mes específico"""
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        
        payments = Payment.objects.filter(
            date_payment__gte=month_start,
            date_payment__lte=month_end
        )
        
        # Estadísticas básicas
        total_collected = payments.filter(is_fully_paid=True).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        pending_amount = Payment.objects.filter(
            is_fully_paid=False,
            due_date__gte=month_start,
            due_date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        overdue_amount = Payment.objects.filter(
            is_fully_paid=False,
            due_date__lt=month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        payment_count = payments.count()
        
        # Tasa de recaudación
        total_expected = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        collection_rate = (total_collected / total_expected * 100) if total_expected > 0 else Decimal('0')
        
        return {
            'year': year,
            'month': month,
            'total_collected': total_collected,
            'pending_amount': pending_amount,
            'overdue_amount': overdue_amount,
            'payment_count': payment_count,
            'collection_rate': collection_rate,
            'period': month_start.strftime('%Y-%m')
        }
    
    @classmethod
    def get_payment_trends(cls, period_months=6, user_email=None, payment_method=None):
        """
        Obtiene tendencias de pagos para los últimos N meses con filtros opcionales
        
        Args:
            period_months: Período en meses (default: 6)
            user_email: Filtrar por email de usuario (opcional)
            payment_method: Filtrar por método de pago (opcional)
        """
        today = date.today()
        start_date = today.replace(day=1) - timedelta(days=period_months * 30)
        
        # Base queryset con filtros
        base_queryset = Payment.objects.all()
        if user_email:
            base_queryset = base_queryset.filter(user__email__icontains=user_email)
        
        # Agrupar por mes
        trends = []
        current_date = start_date
        
        while current_date <= today:
            month_start = current_date.replace(day=1)
            if current_date.month == 12:
                month_end = date(current_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(current_date.year, current_date.month + 1, 1) - timedelta(days=1)
            
            payments = base_queryset.filter(
                date_payment__gte=month_start,
                date_payment__lte=month_end
            )
            
            # Filtrar por método de pago si se especifica
            if payment_method:
                transaction_ids = PaymentTransaction.objects.filter(
                    payment_method=payment_method
                ).values_list('payment_id', flat=True)
                payments = payments.filter(id__in=transaction_ids)
            
            total_collected = payments.filter(is_fully_paid=True).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            trends.append({
                'month': month_start.strftime('%Y-%m'),
                'total_collected': total_collected,
                'payment_count': payments.count()
            })
            
            # Siguiente mes
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return trends
    
    @classmethod
    def get_top_payers(cls, limit=10, user_email=None, payment_method=None):
        """
        Obtiene los usuarios con mejor historial de pagos con filtros opcionales
        
        Args:
            limit: Número máximo de resultados (default: 10)
            user_email: Filtrar por email de usuario (opcional)
            payment_method: Filtrar por método de pago (opcional)
        """
        from django.db.models import F, Case, When, DecimalField
        
        # Base queryset con filtros
        base_queryset = Payment.objects.all()
        if user_email:
            base_queryset = base_queryset.filter(user__email__icontains=user_email)
        
        # Filtrar por método de pago si se especifica
        if payment_method:
            transaction_ids = PaymentTransaction.objects.filter(
                payment_method=payment_method
            ).values_list('payment_id', flat=True)
            base_queryset = base_queryset.filter(id__in=transaction_ids)
        
        # Calcular puntuación basada en pagos completos y puntualidad
        top_payers = base_queryset.values('user__email', 'user__first_name', 'user__last_name').annotate(
            total_paid=Sum('amount_paid'),
            total_expected=Sum('amount'),
            payment_count=Count('id'),
            on_time_payments=Count(
                Case(
                    When(
                        Q(is_fully_paid=True) & Q(due_date__gte=F('date_payment')),
                        then=1
                    ),
                    output_field=DecimalField()
                )
            ),
            score=Case(
                When(total_expected__gt=0, then=F('total_paid') / F('total_expected') * 100),
                default=0,
                output_field=DecimalField()
            )
        ).filter(
            total_paid__gt=0
        ).order_by('-score', '-on_time_payments')[:limit]
        
        return list(top_payers)
    
    @classmethod
    def get_payment_methods_distribution(cls):
        """Obtiene la distribución de pagos por método de pago"""
        distribution = PaymentTransaction.objects.values('payment_method').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).exclude(payment_method__isnull=True).exclude(payment_method='')
        
        return list(distribution)
    
    @classmethod
    def generate_monthly_stats(cls, year, month):
        """Genera y guarda estadísticas para un mes específico"""
        stats_data = cls.get_monthly_stats(year, month)
        
        # Crear o actualizar estadísticas
        month_start = date(year, month, 1)
        stats, created = PaymentStats.objects.get_or_create(
            date=month_start,
            defaults=stats_data
        )
        
        if not created:
            # Actualizar estadísticas existentes
            stats.total_collected = stats_data['total_collected']
            stats.pending_amount = stats_data['pending_amount']
            stats.overdue_amount = stats_data['overdue_amount']
            stats.payment_count = stats_data['payment_count']
            stats.collection_rate = stats_data['collection_rate']
            stats.save()
        
        return stats
