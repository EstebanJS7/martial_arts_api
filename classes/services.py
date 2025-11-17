"""
Servicio para calcular estadísticas de clases y generar datos para el dashboard.
"""
from django.db import transaction
from django.db.models import Count, Avg, Q, Sum, F
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from datetime import timedelta, date
from decimal import Decimal

from .models import (
    Class,
    UserClassReservation,
    ClassAttendance,
    ClassTemplate,
    ClassWaitlist,
)
from .validators import ClassValidator
from notifications.notification_scheduler import NotificationScheduler
from notifications.services import create_and_notify


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


class ClassManagementService:
    """
    Servicio para operaciones avanzadas de gestión de clases.
    """

    @staticmethod
    def _make_aware(dt):
        if dt and timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    @staticmethod
    def _generate_recurrence_dates(start_date, end_date=None, occurrences=4, frequency='weekly', days_of_week=None):
        """
        Genera una lista de fechas basadas en la recurrencia solicitada.
        days_of_week sigue el formato Python (0 = lunes ... 6 = domingo).
        """
        if occurrences < 1:
            occurrences = 1

        dates = []
        current = start_date
        allowed_days = days_of_week or [start_date.weekday()]

        if frequency == 'daily':
            while len(dates) < occurrences and (end_date is None or current <= end_date):
                if current >= start_date:
                    dates.append(current)
                current += timedelta(days=1)
        elif frequency == 'weekly':
            # Iterar día a día hasta cumplir condiciones
            while len(dates) < occurrences and (end_date is None or current <= end_date):
                if current.weekday() in allowed_days and current >= start_date:
                    dates.append(current)
                current += timedelta(days=1)
        elif frequency == 'monthly':
            helper_date = start_date
            while len(dates) < occurrences and (end_date is None or helper_date <= end_date):
                dates.append(helper_date)
                # Calcular siguiente mes conservando hora/minuto
                year = helper_date.year + (helper_date.month // 12)
                month = helper_date.month % 12 + 1
                day = helper_date.day
                # Ajustar día al final de mes si necesario
                for day_option in range(day, 0, -1):
                    try:
                        helper_date = helper_date.replace(year=year, month=month, day=day_option)
                        break
                    except ValueError:
                        continue
            # Si no se generaron fechas (por ejemplo, day 31), garantizar al menos una
            if not dates:
                dates.append(start_date)
        else:
            dates.append(start_date)

        return dates[:occurrences]

    @staticmethod
    def create_recurring_classes(user, base_data, recurrence_settings):
        """
        Crea clases recurrentes a partir de un conjunto de parámetros o una plantilla.
        Retorna un diccionario con el resumen de creación.
        """
        template = None
        template_id = recurrence_settings.get('template_id')
        if template_id:
            try:
                template = ClassTemplate.objects.get(pk=template_id)
            except ClassTemplate.DoesNotExist:
                raise ObjectDoesNotExist("La plantilla especificada no existe.")

        start_date = ClassManagementService._make_aware(recurrence_settings['start_date'])
        end_date = ClassManagementService._make_aware(recurrence_settings.get('end_date')) if recurrence_settings.get('end_date') else None
        occurrences = recurrence_settings.get('occurrences', 4)
        frequency = recurrence_settings.get('frequency', 'weekly')
        days_of_week = recurrence_settings.get('days_of_week')

        base_payload = {}
        if template:
            base_payload.update({
                'name': template.name,
                'description': template.description,
                'instructor': template.instructor,
                'duration': template.duration,
                'max_students': template.max_students,
                'class_type': template.class_type,
                'difficulty_level': template.difficulty_level,
                'location': template.location,
                'equipment_needed': template.equipment_needed,
                'notes': template.prerequisites,
            })
        base_payload.update(base_data)

        if not base_payload.get('name'):
            raise ValueError("El nombre de la clase es obligatorio.")
        if not base_payload.get('instructor'):
            raise ValueError("Se requiere un instructor para crear clases.")
        if not base_payload.get('max_students'):
            raise ValueError("Debe especificarse la capacidad máxima de estudiantes.")

        duration_minutes = base_payload.pop('duration_minutes', None)
        duration_field = base_payload.get('duration')

        if duration_minutes:
            base_payload['duration'] = timedelta(minutes=duration_minutes)
        elif isinstance(duration_field, (int, float)):
            base_payload['duration'] = timedelta(minutes=duration_field)

        schedule = ClassManagementService._generate_recurrence_dates(
            start_date=start_date,
            end_date=end_date,
            occurrences=occurrences,
            frequency=frequency,
            days_of_week=days_of_week,
        )

        created_instances = []
        validation_errors = []

        with transaction.atomic():
            for scheduled_date in schedule:
                class_data = {
                    **base_payload,
                    'date': scheduled_date,
                }

                validation_result = ClassValidator.validate_class(class_data)
                if not validation_result['valid']:
                    validation_errors.append({
                        'date': scheduled_date.isoformat(),
                        'errors': validation_result['errors'],
                    })
                    continue

                instance = Class.objects.create(**class_data)
                created_instances.append(instance)

        return {
            'created': len(created_instances),
            'errors': validation_errors,
            'classes': created_instances,
        }

    @staticmethod
    def check_attendance(class_obj, marked_by=None):
        """
        Garantiza que todas las reservas tengan un registro de asistencia asociado.
        """
        reservations = UserClassReservation.objects.filter(
            class_reserved=class_obj,
            is_cancelled=False,
        ).select_related('user')

        created_count = 0

        for reservation in reservations:
            attendance, created = ClassAttendance.objects.get_or_create(
                class_reserved=class_obj,
                user=reservation.user,
                defaults={
                    'attended': False,
                    'marked_by': marked_by,
                },
            )
            if created:
                created_count += 1

        attendance_count = ClassAttendance.objects.filter(
            class_reserved=class_obj,
            attended=True,
        ).count()
        no_show_count = ClassAttendance.objects.filter(
            class_reserved=class_obj,
            attended=False,
        ).count()

        Class.objects.filter(pk=class_obj.pk).update(
            attendance_count=attendance_count,
            no_show_count=no_show_count,
        )

        return {
            'created_records': created_count,
            'attendance_count': attendance_count,
            'no_show_count': no_show_count,
            'total_reservations': reservations.count(),
        }

    @staticmethod
    def get_class_statistics(class_obj):
        """
        Retorna estadísticas detalladas de una clase específica.
        """
        reservations = UserClassReservation.objects.filter(
            class_reserved=class_obj,
            is_cancelled=False,
        )
        attendance_qs = ClassAttendance.objects.filter(class_reserved=class_obj)

        attendance_count = attendance_qs.filter(attended=True).count()
        no_show_count = attendance_qs.filter(attended=False).count()
        waitlist_count = class_obj.waitlist_entries.filter(status='waiting').count()

        attendance_rate = 0.0
        if reservations.count() > 0:
            attendance_rate = (attendance_count / reservations.count()) * 100

        return {
            'class_id': class_obj.id,
            'name': class_obj.name,
            'date': class_obj.date,
            'instructor_id': class_obj.instructor_id,
            'reservation_count': class_obj.reservation_count,
            'max_students': class_obj.max_students,
            'available_spots': max(0, class_obj.max_students - class_obj.reservation_count),
            'attendance_count': attendance_count,
            'attendance_rate': round(attendance_rate, 2),
            'no_show_count': no_show_count,
            'waitlist_count': waitlist_count,
            'is_cancelled': class_obj.is_cancelled,
            'cancellation_reason': class_obj.cancellation_reason,
        }

    @staticmethod
    def send_class_reminders(class_obj=None, reminder_type='auto'):
        """
        Envía recordatorios de clases. Si se especifica class_obj, envía notificaciones inmediatas.
        Caso contrario, ejecuta el proceso completo de recordatorios programados.
        """
        if class_obj:
            reservations = UserClassReservation.objects.filter(
                class_reserved=class_obj,
                is_cancelled=False,
            )
            notifications = 0
            for reservation in reservations:
                title = 'Recordatorio de clase'
                if reminder_type == '24h':
                    title = 'Recordatorio: Clase mañana'
                elif reminder_type == '1h':
                    title = '¡Clase en 1 hora!'

                message = f'Recordatorio: Tienes la clase {class_obj.name} el {class_obj.date:%d/%m/%Y %H:%M}.'

                create_and_notify(
                    recipient_id=reservation.user_id,
                    title=title,
                    message=message,
                    ntype='class',
                    payload={
                        'class_id': class_obj.id,
                        'reservation_id': reservation.id,
                        'reminder_type': reminder_type,
                    },
                )
                notifications += 1
            return {'notifications_sent': notifications, 'class_id': class_obj.id, 'reminder_type': reminder_type}

        return NotificationScheduler.process_all_reminders()








