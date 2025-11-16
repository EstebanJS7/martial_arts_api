"""
Servicio para calcular estadísticas de clases y generar datos para el dashboard.
"""
from django.db.models import Count, Avg, Q, Sum, F
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

from .models import Class, UserClassReservation, ClassAttendance, ClassTemplate


class ClassDashboardService:
    """
    Servicio para generar estadísticas y datos del dashboard de clases.
    """
    
    @classmethod
    def get_dashboard_overview(cls, period_months=1, instructor_id=None, start_date=None, end_date=None):
        """
        Obtiene métricas principales para el dashboard de clases con filtros opcionales
        
        Args:
            period_months: Período en meses para calcular métricas (default: 1 = mes actual)
            instructor_id: Filtrar por instructor (opcional)
            start_date: Fecha de inicio para filtrar (opcional)
            end_date: Fecha de fin para filtrar (opcional)
        """
        today = timezone.now().date()
        
        # Determinar rango de fechas basado en período
        if start_date and end_date:
            period_start = start_date
            period_end = end_date
        else:
            period_start = today.replace(day=1) - timedelta(days=(period_months - 1) * 30)
            period_end = today
        
        # Base queryset con filtros
        base_queryset = Class.objects.all()
        
        # Filtrar por instructor si se especifica
        if instructor_id:
            base_queryset = base_queryset.filter(instructor_id=instructor_id)
        
        # Clases en el período
        classes_in_period = base_queryset.filter(
            date__date__gte=period_start,
            date__date__lte=period_end
        )
        
        # Clases pasadas y futuras
        past_classes = classes_in_period.filter(date__lt=timezone.now())
        upcoming_classes = classes_in_period.filter(date__gte=timezone.now())
        
        # Métricas principales
        total_classes = classes_in_period.count()
        past_classes_count = past_classes.count()
        upcoming_classes_count = upcoming_classes.count()
        
        # Total de reservas
        reservations_in_period = UserClassReservation.objects.filter(
            class_reserved__in=classes_in_period,
            is_cancelled=False
        )
        total_reservations = reservations_in_period.count()
        
        # Asistencia promedio
        attendance_records = ClassAttendance.objects.filter(
            class_reserved__in=past_classes,
            attended=True
        )
        attendance_count = attendance_records.count()
        
        # Calcular tasa de asistencia
        total_past_reservations = UserClassReservation.objects.filter(
            class_reserved__in=past_classes,
            is_cancelled=False
        ).count()
        attendance_rate = (attendance_count / total_past_reservations * 100) if total_past_reservations > 0 else Decimal('0')
        
        # Ocupación promedio
        avg_occupancy = classes_in_period.aggregate(
            avg=Avg(F('reservation_count') * 100.0 / F('max_students'))
        )['avg'] or Decimal('0')
        
        # Clases completas
        full_classes = classes_in_period.filter(
            reservation_count__gte=F('max_students')
        ).count()
        
        period_str = f"{period_start.strftime('%Y-%m')} a {period_end.strftime('%Y-%m')}" if period_months > 1 else period_start.strftime('%Y-%m')
        
        return {
            'total_classes': total_classes,
            'past_classes': past_classes_count,
            'upcoming_classes': upcoming_classes_count,
            'total_reservations': total_reservations,
            'attendance_count': attendance_count,
            'attendance_rate': float(attendance_rate),
            'avg_occupancy': float(avg_occupancy),
            'full_classes': full_classes,
            'period': period_str
        }
    
    @classmethod
    def get_monthly_stats(cls, year, month, instructor_id=None):
        """
        Obtiene estadísticas detalladas para un mes específico
        """
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        
        classes = Class.objects.filter(
            date__date__gte=month_start,
            date__date__lte=month_end
        )
        
        if instructor_id:
            classes = classes.filter(instructor_id=instructor_id)
        
        total_classes = classes.count()
        total_reservations = UserClassReservation.objects.filter(
            class_reserved__in=classes,
            is_cancelled=False
        ).count()
        
        past_classes = classes.filter(date__lt=timezone.now())
        attendance_count = ClassAttendance.objects.filter(
            class_reserved__in=past_classes,
            attended=True
        ).count()
        
        return {
            'year': year,
            'month': month,
            'total_classes': total_classes,
            'total_reservations': total_reservations,
            'attendance_count': attendance_count,
        }
    
    @classmethod
    def get_class_trends(cls, period_months=6, instructor_id=None):
        """
        Obtiene tendencias de clases mes a mes
        """
        today = timezone.now().date()
        trends = []
        
        for i in range(period_months):
            month_date = today.replace(day=1) - timedelta(days=30 * i)
            month_start = month_date.replace(day=1)
            if month_date.month == 12:
                month_end = date(month_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(month_date.year, month_date.month + 1, 1) - timedelta(days=1)
            
            classes = Class.objects.filter(
                date__date__gte=month_start,
                date__date__lte=month_end
            )
            
            if instructor_id:
                classes = classes.filter(instructor_id=instructor_id)
            
            total_classes = classes.count()
            total_reservations = UserClassReservation.objects.filter(
                class_reserved__in=classes,
                is_cancelled=False
            ).count()
            
            past_classes = classes.filter(date__lt=timezone.now())
            attendance_count = ClassAttendance.objects.filter(
                class_reserved__in=past_classes,
                attended=True
            ).count()
            
            trends.append({
                'period': month_start.strftime('%Y-%m'),
                'total_classes': total_classes,
                'total_reservations': total_reservations,
                'attendance_count': attendance_count,
            })
        
        return list(reversed(trends))
    
    @classmethod
    def get_top_instructors(cls, period_months=1, limit=10):
        """
        Obtiene los instructores con más clases y mejores estadísticas
        """
        today = timezone.now().date()
        period_start = today.replace(day=1) - timedelta(days=(period_months - 1) * 30)
        
        classes = Class.objects.filter(
            date__date__gte=period_start,
            date__date__lte=today
        )
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        instructors = User.objects.filter(
            instructed_classes__in=classes
        ).annotate(
            total_classes=Count('instructed_classes'),
            total_reservations=Count(
                'instructed_classes__userclassreservation',
                filter=Q(instructed_classes__userclassreservation__is_cancelled=False)
            ),
            avg_occupancy=Avg(
                F('instructed_classes__reservation_count') * 100.0 / F('instructed_classes__max_students'),
                filter=Q(instructed_classes__date__date__gte=period_start)
            )
        ).order_by('-total_classes')[:limit]
        
        result = []
        for instructor in instructors:
            past_classes = instructor.instructed_classes.filter(
                date__date__gte=period_start,
                date__date__lte=today,
                date__lt=timezone.now()
            )
            attendance_count = ClassAttendance.objects.filter(
                class_reserved__in=past_classes,
                attended=True
            ).count()
            total_reservations_past = UserClassReservation.objects.filter(
                class_reserved__in=past_classes,
                is_cancelled=False
            ).count()
            attendance_rate = (attendance_count / total_reservations_past * 100) if total_reservations_past > 0 else 0
            
            result.append({
                'id': instructor.id,
                'email': instructor.email,
                'first_name': instructor.first_name,
                'last_name': instructor.last_name,
                'total_classes': instructor.total_classes,
                'total_reservations': instructor.total_reservations,
                'avg_occupancy': float(instructor.avg_occupancy or 0),
                'attendance_rate': float(attendance_rate),
            })
        
        return result
    
    @classmethod
    def get_classes_by_type(cls, period_months=1):
        """
        Distribución de clases por tipo (si el modelo Class tiene tipo)
        """
        today = timezone.now().date()
        period_start = today.replace(day=1) - timedelta(days=(period_months - 1) * 30)
        
        classes = Class.objects.filter(
            date__date__gte=period_start,
            date__date__lte=today
        )
        
        # Si las plantillas tienen tipo, podemos usar eso como referencia
        # Por ahora, retornamos estadísticas básicas
        templates = ClassTemplate.objects.filter(is_active=True)
        distribution = {}
        
        for template in templates:
            template_classes = classes.filter(
                name__icontains=template.name.split()[0]  # Simplificado
            ).count()
            if template_classes > 0:
                distribution[template.class_type] = distribution.get(template.class_type, 0) + template_classes
        
        return distribution
    
    @classmethod
    def get_popular_classes(cls, period_months=1, limit=10):
        """
        Obtiene las clases más populares (con más reservas)
        """
        today = timezone.now().date()
        period_start = today.replace(day=1) - timedelta(days=(period_months - 1) * 30)
        
        classes = Class.objects.filter(
            date__date__gte=period_start,
            date__date__lte=today
        ).annotate(
            reservation_count_calc=Count(
                'userclassreservation',
                filter=Q(userclassreservation__is_cancelled=False)
            )
        ).order_by('-reservation_count_calc')[:limit]
        
        result = []
        for class_obj in classes:
            past_class = class_obj.date < timezone.now()
            attendance_count = 0
            attendance_rate = 0
            if past_class:
                attendance_count = ClassAttendance.objects.filter(
                    class_reserved=class_obj,
                    attended=True
                ).count()
                total_reservations_past = UserClassReservation.objects.filter(
                    class_reserved=class_obj,
                    is_cancelled=False
                ).count()
                attendance_rate = (attendance_count / total_reservations_past * 100) if total_reservations_past > 0 else 0
            
            result.append({
                'id': class_obj.id,
                'name': class_obj.name,
                'date': class_obj.date.isoformat(),
                'instructor_name': f"{class_obj.instructor.first_name or ''} {class_obj.instructor.last_name or ''}".strip() if class_obj.instructor else '',
                'instructor_email': class_obj.instructor.email if class_obj.instructor else '',
                'reservation_count': class_obj.reservation_count_calc,
                'max_students': class_obj.max_students,
                'occupancy_rate': float(class_obj.reservation_count_calc * 100 / class_obj.max_students) if class_obj.max_students > 0 else 0,
                'attendance_count': attendance_count,
                'attendance_rate': float(attendance_rate),
            })
        
        return result







