# views.py
import logging
from django.db import transaction
from django.db.models import F, Count, Q
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist

from .models import Class, UserClassReservation, ClassAttendance, ClassTemplate, ClassWaitlist
from .services import ClassDashboardService, ClassManagementService
from .qr_utils import generate_qr_code_image, validate_qr_token_and_checkin
from .export_service import ClassExportService
from .validators import ClassValidator
from .serializers import (
    ClassSerializer, 
    UserClassReservationSerializer, 
    MultiClassCreateSerializer,
    MultiClassUpdateSerializer,
    ClassAttendanceSerializer,
    ClassAttendanceCreateSerializer,
    ClassTemplateSerializer,
    ClassWaitlistSerializer,
    ClassWaitlistCreateSerializer,
    RecurringClassCreateSerializer,
    ClassReminderTriggerSerializer,
)
from users.permissions import IsAdminUser, IsInstructorUser
from rest_framework.permissions import IsAuthenticated, AllowAny, AllowAny

# Configurar el logger
logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# --- Vistas para Clases ---

class ClassCreateView(generics.CreateAPIView):
    """
    Permite la creación de una clase individual.
    Solo administradores e instructores pueden crear clases.
    """
    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def perform_create(self, serializer):
        # Obtener datos validados
        validated_data = serializer.validated_data
        
        # Realizar validaciones avanzadas
        validation_result = ClassValidator.validate_class(validated_data)
        
        if not validation_result['valid']:
            error_message = '; '.join(validation_result['errors'])
            raise ValidationError(error_message)
        
        # Si hay advertencias, registrarlas pero permitir la creación
        if validation_result.get('warnings'):
            logger.warning(f"Advertencias al crear clase: {'; '.join(validation_result['warnings'])}")
        
        # Crear la clase
        serializer.save()

class MultiClassCreateView(APIView):
    """
    Permite crear múltiples clases de una sola vez.
    Recibe un listado de clases.
    Solo administradores e instructores pueden usar este endpoint.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]

    def post(self, request):
        serializer = MultiClassCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Validar cada clase antes de crearlas
            classes_data = serializer.validated_data.get('classes', [])
            validation_errors = []
            
            for idx, class_data in enumerate(classes_data):
                validation_result = ClassValidator.validate_class(class_data)
                if not validation_result['valid']:
                    validation_errors.append({
                        'index': idx,
                        'class_name': class_data.get('name', 'Sin nombre'),
                        'errors': validation_result['errors']
                    })
            
            if validation_errors:
                return Response({
                    'detail': 'Errores de validación en algunas clases',
                    'validation_errors': validation_errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            classes = serializer.save()
            logger.info(f"{request.user.email} creó {len(classes)} clases de forma masiva.")
            return Response(ClassSerializer(classes, many=True).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ClassListView(generics.ListAPIView):
    """
    Lista todas las clases.
    """
    serializer_class = ClassSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        # Optimización: Usar select_related para cargar el instructor en una sola consulta
        queryset = Class.objects.select_related('instructor').all()
        
        # Filtrar por fecha (clases futuras por defecto)
        show_past = self.request.query_params.get('show_past', 'false').lower() == 'true'
        if not show_past:
            queryset = queryset.filter(date__gte=timezone.now())
            
        # Ordenar por fecha (las más próximas primero)
        queryset = queryset.order_by('date')
        
        return queryset

class ClassDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Permite obtener, actualizar o eliminar una clase específica.
    Solo administradores e instructores.
    """
    serializer_class = ClassSerializer
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get_queryset(self):
        # Optimización: Usar select_related para cargar el instructor en una sola consulta
        return Class.objects.select_related('instructor')
    
    def perform_update(self, serializer):
        # Obtener datos validados
        validated_data = serializer.validated_data
        instance = self.get_object()
        
        # Combinar datos actuales con los nuevos
        class_data = {
            'instructor': validated_data.get('instructor', instance.instructor_id),
            'date': validated_data.get('date', instance.date),
            'duration': validated_data.get('duration', instance.duration),
            'location': validated_data.get('location', instance.location),
            'max_students': validated_data.get('max_students', instance.max_students),
            'equipment_needed': validated_data.get('equipment_needed', instance.equipment_needed),
        }
        
        # Realizar validaciones avanzadas
        validation_result = ClassValidator.validate_class(class_data, exclude_class_id=instance.id)
        
        if not validation_result['valid']:
            error_message = '; '.join(validation_result['errors'])
            raise ValidationError(error_message)
        
        # Si hay advertencias, registrarlas pero permitir la actualización
        if validation_result.get('warnings'):
            logger.warning(f"Advertencias al actualizar clase {instance.id}: {'; '.join(validation_result['warnings'])}")
        
        # Actualizar la clase
        serializer.save()

class MultiClassUpdateView(APIView):
    """
    Permite actualizar múltiples clases a la vez.
    Se espera recibir un objeto con un campo 'classes' que contenga una lista de actualizaciones.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]

    def put(self, request):
        classes_data = request.data.get('classes', [])
        if not isinstance(classes_data, list):
            return Response({"error": "El campo 'classes' debe ser una lista."}, status=status.HTTP_400_BAD_REQUEST)
        updated_classes = []
        with transaction.atomic():
            for class_data in classes_data:
                try:
                    instance = Class.objects.get(pk=class_data.get('id'))
                except Class.DoesNotExist:
                    continue  # O retornar un error para ese elemento
                serializer = MultiClassUpdateSerializer(instance, data=class_data, partial=True)
                if serializer.is_valid():
                    updated_instance = serializer.save()
                    updated_classes.append(updated_instance)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        logger.info(f"{request.user.email} realizó una actualización masiva de clases.")
        return Response(ClassSerializer(updated_classes, many=True).data, status=status.HTTP_200_OK)

# --- Vistas para Reservas ---

class UserClassReservationCreateView(generics.CreateAPIView):
    """
    Permite a un usuario autenticado reservar una clase.
    Se valida la concurrencia y se actualiza el contador de reservas.
    """
    queryset = UserClassReservation.objects.all()
    serializer_class = UserClassReservationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def perform_create(self, serializer):
        class_to_reserve = serializer.validated_data['class_reserved']
        
        # Usar select_for_update para bloquear la fila durante la transacción
        class_obj = Class.objects.select_for_update().get(pk=class_to_reserve.pk)
        
        # Verificar que la clase sea futura
        now = timezone.now()
        if class_obj.date <= now:
            raise ValidationError("No se puede reservar una clase que ya pasó o está en curso.")
        
        # Verificar si la clase está llena
        if class_obj.reservation_count >= class_obj.max_students:
            raise ValidationError("La clase está llena.")
            
        # Verificar si el usuario ya tiene una reserva para esta clase
        if UserClassReservation.objects.filter(
            user=self.request.user,
            class_reserved=class_obj
        ).exists():
            raise ValidationError("Ya tienes una reserva para esta clase.")
        
        # Validar prerequisitos del estudiante
        validation_result = ClassValidator.validate_student_prerequisites(
            self.request.user.id,
            class_obj.difficulty_level,
            class_obj.class_type
        )
        
        if not validation_result['valid']:
            raise ValidationError(validation_result['message'])
            
        # Incrementar el contador de reservas usando update para evitar problemas con F()
        Class.objects.filter(pk=class_obj.pk).update(reservation_count=F('reservation_count') + 1)
        
        # Refrescar el objeto desde la base de datos para obtener el valor actualizado
        class_obj.refresh_from_db()
        
        # Guardar la reserva
        serializer.save(user=self.request.user)

class UserClassReservationCancelView(generics.DestroyAPIView):
    """
    Permite cancelar (eliminar) una reserva.
    Solo el usuario que realizó la reserva o un administrador puede cancelar.
    """
    queryset = UserClassReservation.objects.all()
    serializer_class = UserClassReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        reservation = super().get_object()
        if reservation.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("No tienes permiso para cancelar esta reserva.")
        return reservation

    def perform_destroy(self, instance):
        with transaction.atomic():
            class_reserved = Class.objects.select_for_update().get(pk=instance.class_reserved.pk)
            class_reserved.reservation_count = F('reservation_count') - 1
            class_reserved.save()
            instance.delete()
        logger.info(f"{self.request.user.email} canceló su reserva para la clase '{class_reserved.name}'.")

class UserClassReservationUpdateView(generics.UpdateAPIView):
    """
    Permite a un usuario modificar su reserva, por ejemplo, cambiar la clase reservada.
    Se actualizan los contadores de la clase original y la nueva, si es necesario.
    """
    queryset = UserClassReservation.objects.all()
    serializer_class = UserClassReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        reservation = super().get_object()
        if reservation.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("No tienes permiso para modificar esta reserva.")
        return reservation

    def perform_update(self, serializer):
        old_reservation = self.get_object()
        new_class = serializer.validated_data.get('class_reserved', old_reservation.class_reserved)
        if new_class != old_reservation.class_reserved:
            with transaction.atomic():
                old_class = Class.objects.select_for_update().get(pk=old_reservation.class_reserved.pk)
                new_class_obj = Class.objects.select_for_update().get(pk=new_class.pk)
                if new_class_obj.reservation_count >= new_class_obj.max_students:
                    raise ValidationError({"detail": "La nueva clase está completamente reservada."})
                old_class.reservation_count = F('reservation_count') - 1
                old_class.save()
                new_class_obj.reservation_count = F('reservation_count') + 1
                new_class_obj.save()
        serializer.save()
        logger.info(f"{self.request.user.email} actualizó su reserva (ID: {old_reservation.pk}).")

class MyClassReservationsView(generics.ListAPIView):
    """
    Lista las reservas activas del usuario autenticado con detalles de cada clase.
    """
    serializer_class = UserClassReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            UserClassReservation.objects
            .filter(user=self.request.user, is_cancelled=False)
            .select_related('class_reserved', 'class_reserved__instructor')
            .order_by('-created_at')
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class UpcomingClassesView(APIView):
    """
    Vista para obtener las próximas clases programadas.
    Muestra clases de los próximos 30 días con información completa del instructor.
    Permite acceso público para la landing page.
    """
    permission_classes = [AllowAny]
    throttle_classes = []  # Deshabilitar throttling para endpoints públicos
    
    def get(self, request):
        # Obtener la fecha actual
        now = timezone.now()
        
        # Obtener las clases que ocurrirán en los próximos 30 días
        end_date = now + timedelta(days=30)
        
        # Filtrar las clases por fecha y optimizar consultas
        upcoming_classes = Class.objects.filter(
            date__gte=now,
            date__lte=end_date
        ).select_related('instructor').order_by('date')
        
        # Construir mapa de reservas del usuario autenticado para estas clases
        user_reservations_map = {}
        if request.user.is_authenticated:
            user_reservations = UserClassReservation.objects.filter(
                user=request.user,
                class_reserved__in=upcoming_classes,
                is_cancelled=False
            ).select_related('class_reserved')
            user_reservations_map = {
                reservation.class_reserved_id: reservation
                for reservation in user_reservations
            }
        
        # Serializar las clases con el contexto para el request
        serializer = ClassSerializer(
            upcoming_classes,
            many=True,
            context={
                'request': request,
                'user_reservations_map': user_reservations_map
            }
        )
        
        return Response(serializer.data)


class UserClassesView(APIView):
    """
    Vista para obtener las clases reservadas por el usuario autenticado.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Obtener las reservas del usuario
        user_reservations = UserClassReservation.objects.filter(
            user=request.user
        ).select_related('class_reserved', 'class_reserved__instructor')
        
        # Serializar las clases reservadas
        classes_data = []
        for reservation in user_reservations:
            class_data = ClassSerializer(reservation.class_reserved).data
            class_data['reservation_id'] = reservation.id
            class_data['reservation_created_at'] = reservation.created_at
            classes_data.append(class_data)
        
        return Response(classes_data)

class AllClassesView(APIView):
    """
    Vista para obtener todas las clases disponibles (pasadas y futuras).
    Útil para mostrar un historial completo o todas las clases del sistema.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Obtener todas las clases ordenadas por fecha
        all_classes = Class.objects.filter(
            date__gte=timezone.now() - timedelta(days=30)  # Últimos 30 días
        ).select_related('instructor').order_by('-date')
        
        # Serializar las clases con el contexto para el request
        serializer = ClassSerializer(all_classes, many=True, context={'request': request})
        
        return Response(serializer.data)


# --- Vistas para Asistencia de Clases ---

class ClassAttendanceListView(APIView):
    """
    Vista para listar asistencias de una clase específica.
    Solo admin/instructor pueden ver las asistencias.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get(self, request, class_id):
        try:
            class_obj = Class.objects.get(pk=class_id)
        except Class.DoesNotExist:
            return Response(
                {"detail": "Clase no encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Obtener todas las reservas de la clase
        reservations = UserClassReservation.objects.filter(
            class_reserved=class_obj,
            is_cancelled=False
        ).select_related('user')
        
        # Obtener asistencias existentes
        attendances = ClassAttendance.objects.filter(
            class_reserved=class_obj
        ).select_related('user', 'marked_by')
        
        attendance_dict = {att.user_id: att for att in attendances}
        
        # Crear lista de asistencias (incluyendo reservas sin registro de asistencia)
        result = []
        for reservation in reservations:
            if reservation.user_id in attendance_dict:
                att = attendance_dict[reservation.user_id]
                serializer = ClassAttendanceSerializer(att)
                result.append(serializer.data)
            else:
                # Crear entrada sin asistencia marcada
                result.append({
                    'id': None,
                    'class_reserved': class_obj.id,
                    'user': reservation.user.id,
                    'user_email': reservation.user.email,
                    'user_full_name': f"{reservation.user.first_name or ''} {reservation.user.last_name or ''}".strip() or reservation.user.email,
                    'class_name': class_obj.name,
                    'attended': False,
                    'check_in_time': None,
                    'check_out_time': None,
                    'notes': '',
                    'marked_by': None,
                    'marked_by_email': None,
                    'created_at': reservation.created_at.isoformat(),
                    'updated_at': reservation.created_at.isoformat(),
                })
        
        return Response(result, status=status.HTTP_200_OK)


class ClassAttendanceCreateUpdateView(APIView):
    """
    Vista para crear o actualizar asistencia de un estudiante en una clase.
    Solo admin/instructor pueden marcar asistencia.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def post(self, request, class_id):
        try:
            class_obj = Class.objects.get(pk=class_id)
        except Class.DoesNotExist:
            return Response(
                {"detail": "Clase no encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ClassAttendanceCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.validated_data['user']
        attended = serializer.validated_data.get('attended', True)
        
        # Verificar que el usuario tenga reserva para esta clase
        reservation = UserClassReservation.objects.filter(
            class_reserved=class_obj,
            user=user,
            is_cancelled=False
        ).first()
        
        if not reservation:
            return Response(
                {"detail": "El usuario no tiene reserva para esta clase"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear o actualizar asistencia
        attendance, created = ClassAttendance.objects.update_or_create(
            class_reserved=class_obj,
            user=user,
            defaults={
                'attended': attended,
                'notes': serializer.validated_data.get('notes', ''),
                'check_in_time': serializer.validated_data.get('check_in_time', timezone.now() if attended else None),
                'check_out_time': serializer.validated_data.get('check_out_time'),
                'marked_by': request.user,
            }
        )
        
        result_serializer = ClassAttendanceSerializer(attendance)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ClassAttendanceBulkUpdateView(APIView):
    """
    Vista para actualizar asistencia de múltiples estudiantes a la vez.
    Solo admin/instructor pueden usar este endpoint.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def post(self, request, class_id):
        try:
            class_obj = Class.objects.get(pk=class_id)
        except Class.DoesNotExist:
            return Response(
                {"detail": "Clase no encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        attendances_data = request.data.get('attendances', [])
        if not isinstance(attendances_data, list):
            return Response(
                {"detail": "Se espera una lista de asistencias"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        for attendance_data in attendances_data:
            serializer = ClassAttendanceCreateSerializer(data=attendance_data)
            if not serializer.is_valid():
                results.append({
                    'user': attendance_data.get('user'),
                    'error': serializer.errors
                })
                continue
            
            user = serializer.validated_data['user']
            attended = serializer.validated_data.get('attended', True)
            
            attendance, _ = ClassAttendance.objects.update_or_create(
                class_reserved=class_obj,
                user=user,
                defaults={
                    'attended': attended,
                    'notes': serializer.validated_data.get('notes', ''),
                    'check_in_time': serializer.validated_data.get('check_in_time', timezone.now() if attended else None),
                    'check_out_time': serializer.validated_data.get('check_out_time'),
                    'marked_by': request.user,
                }
            )
            
            result_serializer = ClassAttendanceSerializer(attendance)
            results.append(result_serializer.data)
        
        return Response({'updated': len(results), 'results': results}, status=status.HTTP_200_OK)


# --- Vistas para Plantillas de Clases ---

class ClassTemplateListView(generics.ListCreateAPIView):
    """
    Vista para listar y crear plantillas de clases.
    Solo admin/instructor pueden gestionar plantillas.
    """
    queryset = ClassTemplate.objects.filter(is_active=True)
    serializer_class = ClassTemplateSerializer
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def perform_create(self, serializer):
        serializer.save()


class ClassTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para obtener, actualizar o eliminar una plantilla específica.
    Solo admin/instructor.
    """
    queryset = ClassTemplate.objects.all()
    serializer_class = ClassTemplateSerializer
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def perform_destroy(self, instance):
        # Soft delete: solo desactivar en lugar de eliminar
        instance.is_active = False
        instance.save()
        logger.info(f"{self.request.user.email} desactivó la plantilla '{instance.name}'.")


# --- Vistas para Dashboard de Estadísticas de Clases ---

class ClassDashboardView(APIView):
    """
    Vista para obtener datos del dashboard de clases.
    Solo admin/instructor pueden acceder.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get(self, request):
        period_months = int(request.query_params.get('period_months', 1))
        instructor_id = request.query_params.get('instructor_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Convertir instructor_id a int si existe
        if instructor_id:
            try:
                instructor_id = int(instructor_id)
            except (ValueError, TypeError):
                instructor_id = None
        
        # Convertir fechas si existen
        from datetime import datetime
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                start_date = None
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                end_date = None
        
        data = ClassDashboardService.get_dashboard_overview(
            period_months=period_months,
            instructor_id=instructor_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return Response(data, status=status.HTTP_200_OK)


class ClassStatsView(APIView):
    """
    Vista para obtener estadísticas mensuales de clases.
    Solo admin/instructor.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get(self, request):
        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))
        instructor_id = request.query_params.get('instructor_id')
        
        if instructor_id:
            try:
                instructor_id = int(instructor_id)
            except (ValueError, TypeError):
                instructor_id = None
        
        data = ClassDashboardService.get_monthly_stats(
            year=year,
            month=month,
            instructor_id=instructor_id
        )
        
        return Response(data, status=status.HTTP_200_OK)


class ClassTrendsView(APIView):
    """
    Vista para obtener tendencias de clases mes a mes.
    Solo admin/instructor.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get(self, request):
        period_months = int(request.query_params.get('period_months', 6))
        instructor_id = request.query_params.get('instructor_id')
        
        if instructor_id:
            try:
                instructor_id = int(instructor_id)
            except (ValueError, TypeError):
                instructor_id = None
        
        data = ClassDashboardService.get_class_trends(
            period_months=period_months,
            instructor_id=instructor_id
        )
        
        return Response(data, status=status.HTTP_200_OK)


class TopInstructorsView(APIView):
    """
    Vista para obtener los top instructores por estadísticas.
    Solo admin/instructor.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get(self, request):
        period_months = int(request.query_params.get('period_months', 1))
        limit = int(request.query_params.get('limit', 10))
        
        data = ClassDashboardService.get_top_instructors(
            period_months=period_months,
            limit=limit
        )
        
        return Response(data, status=status.HTTP_200_OK)


class PopularClassesView(APIView):
    """
    Vista para obtener las clases más populares.
    Solo admin/instructor.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get(self, request):
        period_months = int(request.query_params.get('period_months', 1))
        limit = int(request.query_params.get('limit', 10))
        
        data = ClassDashboardService.get_popular_classes(
            period_months=period_months,
            limit=limit
        )
        
        return Response(data, status=status.HTTP_200_OK)


class CancellationAnalysisView(APIView):
    """
    Vista para obtener análisis detallado de cancelaciones de clases.
    Solo admin/instructor.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get(self, request):
        period_months = int(request.query_params.get('period_months', 6))
        instructor_id = request.query_params.get('instructor_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Convertir instructor_id a int si existe
        if instructor_id:
            try:
                instructor_id = int(instructor_id)
            except (ValueError, TypeError):
                instructor_id = None
        
        # Convertir fechas si existen
        from datetime import datetime
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                start_date = None
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                end_date = None
        
        data = ClassDashboardService.get_cancellation_analysis(
            period_months=period_months,
            instructor_id=instructor_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return Response(data, status=status.HTTP_200_OK)


# --- Vistas para Lista de Espera de Clases ---

class ClassWaitlistListView(APIView):
    """
    Lista las entradas de lista de espera.
    - Si se proporciona class_id: lista todas las entradas de espera para esa clase
    - Si no: lista las entradas del usuario actual
    - Admin/Instructor puede ver todas las listas de espera
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        class_id = request.query_params.get('class_id')
        user_id = request.query_params.get('user_id')
        
        # Admin/Instructor puede ver todas las listas de espera
        if (IsAdminUser().has_permission(request, self) or 
            IsInstructorUser().has_permission(request, self)):
            queryset = ClassWaitlist.objects.all()
            
            if class_id:
                queryset = queryset.filter(class_reserved_id=class_id)
            if user_id:
                queryset = queryset.filter(user_id=user_id)
        else:
            # Usuario normal solo ve sus propias entradas
            queryset = ClassWaitlist.objects.filter(user=request.user)
            if class_id:
                queryset = queryset.filter(class_reserved_id=class_id)
        
        # Filtrar por estado si se proporciona
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        serializer = ClassWaitlistSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ClassWaitlistCreateView(APIView):
    """
    Crea una entrada en la lista de espera para una clase llena.
    Solo se puede agregar si la clase está llena y el usuario no tiene ya una reserva o entrada en lista de espera.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ClassWaitlistCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        class_id = serializer.validated_data['class_id']
        
        try:
            class_obj = Class.objects.get(pk=class_id)
        except Class.DoesNotExist:
            return Response(
                {'detail': 'La clase no existe.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar que la clase no esté cancelada
        if class_obj.is_cancelled:
            return Response(
                {'detail': 'No se puede agregar a la lista de espera de una clase cancelada.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que la clase sea futura
        if class_obj.date <= timezone.now():
            return Response(
                {'detail': 'No se puede agregar a la lista de espera de una clase pasada.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que el usuario no tenga ya una reserva
        if UserClassReservation.objects.filter(
            user=request.user,
            class_reserved=class_obj,
            is_cancelled=False
        ).exists():
            return Response(
                {'detail': 'Ya tienes una reserva para esta clase.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que el usuario no esté ya en la lista de espera
        existing_waitlist = ClassWaitlist.objects.filter(
            user=request.user,
            class_reserved=class_obj,
            status='waiting'
        ).first()
        
        if existing_waitlist:
            return Response(
                {'detail': 'Ya estás en la lista de espera para esta clase.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear la entrada en la lista de espera
        waitlist_entry = ClassWaitlist.objects.create(
            user=request.user,
            class_reserved=class_obj,
            status='waiting'
        )
        
        serializer = ClassWaitlistSerializer(waitlist_entry, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ClassWaitlistDeleteView(APIView):
    """
    Elimina/cancela una entrada de la lista de espera.
    El usuario solo puede cancelar sus propias entradas.
    Admin/Instructor puede cancelar cualquier entrada.
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, pk):
        try:
            waitlist_entry = ClassWaitlist.objects.get(pk=pk)
        except ClassWaitlist.DoesNotExist:
            return Response(
                {'detail': 'La entrada de lista de espera no existe.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar permisos
        if waitlist_entry.user != request.user:
            if not (IsAdminUser().has_permission(request, self) or 
                    IsInstructorUser().has_permission(request, self)):
                return Response(
                    {'detail': 'No tienes permiso para eliminar esta entrada.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Solo se puede cancelar si está en espera o notificado
        if waitlist_entry.status not in ['waiting', 'notified']:
            return Response(
                {'detail': 'Solo se pueden cancelar entradas en espera o notificadas.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar el estado a cancelado y compactar las posiciones
        # restantes (1..N) de la lista de espera
        waitlist_entry.leave()

        return Response(
            {'detail': 'Entrada de lista de espera cancelada correctamente.'},
            status=status.HTTP_200_OK
        )


class ClassWaitlistConvertView(APIView):
    """
    Convierte una entrada de lista de espera en una reserva cuando hay cupo disponible.
    Solo se puede convertir si hay cupos disponibles y la entrada está notificada.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        try:
            waitlist_entry = ClassWaitlist.objects.get(pk=pk)
        except ClassWaitlist.DoesNotExist:
            return Response(
                {'detail': 'La entrada de lista de espera no existe.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar que el usuario sea el dueño de la entrada
        if waitlist_entry.user != request.user:
            return Response(
                {'detail': 'No tienes permiso para convertir esta entrada.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verificar que la entrada esté notificada
        if waitlist_entry.status != 'notified':
            return Response(
                {'detail': 'Esta entrada no ha sido notificada aún.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear la reserva bajo bloqueo de fila de la clase (mismo patrón que
        # UserClassReservationCreateView) para que conversiones concurrentes
        # nunca superen la capacidad de la clase.
        with transaction.atomic():
            class_obj = Class.objects.select_for_update().get(
                pk=waitlist_entry.class_reserved_id
            )

            # Verificar que haya cupos disponibles (bajo bloqueo)
            if class_obj.reservation_count >= class_obj.max_students:
                raise ValidationError({'detail': 'Ya no hay cupos disponibles para esta clase.'})

            # Verificar que el usuario no tenga ya una reserva
            if UserClassReservation.objects.filter(
                user=request.user,
                class_reserved=class_obj,
                is_cancelled=False
            ).exists():
                raise ValidationError({'detail': 'Ya tienes una reserva para esta clase.'})

            # Crear la reserva
            reservation = UserClassReservation.objects.create(
                user=request.user,
                class_reserved=class_obj
            )

            # Actualizar el contador de reservas usando update para evitar problemas con F()
            Class.objects.filter(pk=class_obj.pk).update(reservation_count=F('reservation_count') + 1)
            class_obj.refresh_from_db(fields=['reservation_count'])

            # Marcar la entrada como convertida y compactar posiciones restantes
            waitlist_entry.mark_converted()

        return Response(
            {
                'detail': 'Reserva creada correctamente desde la lista de espera.',
                'reservation_id': reservation.id
            },
            status=status.HTTP_200_OK
        )


# --- Vistas para Códigos QR de Check-in ---

class ClassQRCodeView(APIView):
    """
    Vista para generar y obtener el código QR de una clase.
    Solo admin/instructor pueden ver el QR.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get(self, request, class_id):
        try:
            class_obj = Class.objects.get(pk=class_id)
        except Class.DoesNotExist:
            return Response(
                {"detail": "Clase no encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generar token si no existe
        qr_token = class_obj.generate_qr_token()
        
        # Generar datos del QR (URL del frontend con el token)
        from django.conf import settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        qr_data = f"{frontend_url}/checkin?token={qr_token}"
        
        # Generar imagen del QR
        qr_image = generate_qr_code_image(qr_data)
        
        # Devolver imagen como respuesta
        from django.http import HttpResponse
        response = HttpResponse(qr_image, content_type='image/png')
        response['Content-Disposition'] = f'inline; filename="qr_class_{class_obj.id}.png"'
        return response


class ClassQRDataView(APIView):
    """
    Vista para obtener los datos del código QR (token y URL) de una clase.
    Solo admin/instructor pueden ver los datos del QR.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get(self, request, class_id):
        try:
            class_obj = Class.objects.get(pk=class_id)
        except Class.DoesNotExist:
            return Response(
                {"detail": "Clase no encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generar token si no existe
        qr_token = class_obj.generate_qr_token()
        
        # Generar URL del QR
        from django.conf import settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        qr_url = f"{frontend_url}/checkin?token={qr_token}"
        
        return Response({
            'token': qr_token,
            'qr_url': qr_url,
            'class_id': class_obj.id,
            'class_name': class_obj.name,
            'class_date': class_obj.date.isoformat(),
        }, status=status.HTTP_200_OK)


class QRCheckInView(APIView):
    """
    Vista para validar un código QR y realizar check-in automático.
    Cualquier usuario autenticado puede hacer check-in con QR.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        token = request.data.get('token')
        
        if not token:
            return Response(
                {"detail": "Token de QR requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar token y hacer check-in
        result = validate_qr_token_and_checkin(token, request.user)
        
        if not result['success']:
            return Response(
                {"detail": result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(result, status=status.HTTP_200_OK)


# --- Vistas avanzadas de gestión ---

class ClassRecurringCreateView(APIView):
    """
    Crea clases recurrentes basadas en una plantilla o configuración personalizada.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]

    def post(self, request):
        serializer = RecurringClassCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        base_fields = [
            'name',
            'description',
            'instructor',
            'max_students',
            'duration',
            'duration_minutes',
            'class_type',
            'difficulty_level',
            'location',
            'equipment_needed',
            'notes',
        ]
        base_data = {field: validated[field] for field in base_fields if field in validated}

        recurrence_settings = {
            'template_id': validated.get('template_id'),
            'start_date': validated['start_date'],
            'end_date': validated.get('end_date'),
            'occurrences': validated.get('occurrences', 4),
            'frequency': validated.get('frequency', 'weekly'),
            'days_of_week': validated.get('days_of_week'),
        }

        try:
            result = ClassManagementService.create_recurring_classes(
                user=request.user,
                base_data=base_data,
                recurrence_settings=recurrence_settings,
            )
        except ValueError as exc:
            raise ValidationError(str(exc))
        except ObjectDoesNotExist:
            return Response(
                {"detail": "La plantilla especificada no existe."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serialized_classes = ClassSerializer(result['classes'], many=True, context={'request': request})
        response_status = status.HTTP_201_CREATED if result['created'] else status.HTTP_200_OK

        return Response(
            {
                'created': result['created'],
                'errors': result['errors'],
                'classes': serialized_classes.data,
            },
            status=response_status,
        )


class ClassAttendanceHealthCheckView(APIView):
    """
    Garantiza que todas las reservas de una clase tengan registro de asistencia.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]

    def post(self, request, class_id):
        class_obj = get_object_or_404(Class, pk=class_id)
        result = ClassManagementService.check_attendance(class_obj, marked_by=request.user)
        return Response(result, status=status.HTTP_200_OK)


class ClassStatisticsDetailView(APIView):
    """
    Retorna estadísticas detalladas de una clase específica.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]

    def get(self, request, class_id):
        class_obj = get_object_or_404(Class, pk=class_id)
        stats = ClassManagementService.get_class_statistics(class_obj)
        return Response(stats, status=status.HTTP_200_OK)


class ClassReminderTriggerView(APIView):
    """
    Permite lanzar recordatorios de clases de forma manual o automática.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]

    def post(self, request):
        serializer = ClassReminderTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reminder_type = serializer.validated_data.get('reminder_type', 'auto')
        class_id = serializer.validated_data.get('class_id')

        if class_id:
            class_obj = get_object_or_404(Class, pk=class_id)
            result = ClassManagementService.send_class_reminders(class_obj=class_obj, reminder_type=reminder_type)
        else:
            result = ClassManagementService.send_class_reminders(reminder_type=reminder_type)

        return Response(result, status=status.HTTP_200_OK)


# --- Vistas para Exportación de Reportes ---

class AttendanceReportExportView(APIView):
    """
    Exporta reporte de asistencia de una clase en PDF o Excel.
    Solo admin/instructor.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get(self, request, class_id):
        format_type = request.query_params.get('format', 'pdf').lower()
        if format_type not in ['pdf', 'excel']:
            return Response(
                {'error': 'Formato no válido. Use "pdf" o "excel".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            response = ClassExportService.export_attendance_report(class_id, format=format_type)
            return response
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error al exportar reporte de asistencia: {str(e)}")
            return Response(
                {'error': 'Error al generar el reporte.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class InstructorStatisticsExportView(APIView):
    """
    Exporta estadísticas de un instructor en PDF o Excel.
    Solo admin/instructor.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get(self, request, instructor_id):
        format_type = request.query_params.get('format', 'pdf').lower()
        period_months = int(request.query_params.get('period_months', 6))
        
        if format_type not in ['pdf', 'excel']:
            return Response(
                {'error': 'Formato no válido. Use "pdf" o "excel".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            response = ClassExportService.export_instructor_statistics(
                instructor_id, period_months=period_months, format=format_type
            )
            return response
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error al exportar estadísticas de instructor: {str(e)}")
            return Response(
                {'error': 'Error al generar el reporte.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OccupancyAnalysisExportView(APIView):
    """
    Exporta análisis de ocupación en PDF o Excel.
    Solo admin/instructor.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get(self, request):
        format_type = request.query_params.get('format', 'pdf').lower()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if format_type not in ['pdf', 'excel']:
            return Response(
                {'error': 'Formato no válido. Use "pdf" o "excel".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not start_date or not end_date:
            return Response(
                {'error': 'Se requieren las fechas start_date y end_date.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Formato de fecha inválido. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            response = ClassExportService.export_occupancy_analysis(
                start_date, end_date, format=format_type
            )
            return response
        except Exception as e:
            logger.error(f"Error al exportar análisis de ocupación: {str(e)}")
            return Response(
                {'error': 'Error al generar el reporte.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WaitlistReportExportView(APIView):
    """
    Exporta reporte de lista de espera en PDF o Excel.
    Solo admin/instructor.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get(self, request):
        format_type = request.query_params.get('format', 'pdf').lower()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if format_type not in ['pdf', 'excel']:
            return Response(
                {'error': 'Formato no válido. Use "pdf" o "excel".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        start_date_parsed = None
        end_date_parsed = None
        
        if start_date:
            try:
                from datetime import datetime
                start_date_parsed = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Formato de fecha inválido. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if end_date:
            try:
                from datetime import datetime
                end_date_parsed = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Formato de fecha inválido. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            response = ClassExportService.export_waitlist_report(
                start_date=start_date_parsed, end_date=end_date_parsed, format=format_type
            )
            return response
        except Exception as e:
            logger.error(f"Error al exportar reporte de lista de espera: {str(e)}")
            return Response(
                {'error': 'Error al generar el reporte.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CancellationStatisticsExportView(APIView):
    """
    Exporta estadísticas de cancelaciones en PDF o Excel.
    Solo admin/instructor.
    """
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get(self, request):
        format_type = request.query_params.get('format', 'pdf').lower()
        period_months = int(request.query_params.get('period_months', 6))
        instructor_id = request.query_params.get('instructor_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if format_type not in ['pdf', 'excel']:
            return Response(
                {'error': 'Formato no válido. Use "pdf" o "excel".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instructor_id_parsed = None
        if instructor_id:
            try:
                instructor_id_parsed = int(instructor_id)
            except (ValueError, TypeError):
                instructor_id_parsed = None
        
        start_date_parsed = None
        end_date_parsed = None
        
        if start_date:
            try:
                from datetime import datetime
                start_date_parsed = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Formato de fecha inválido. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if end_date:
            try:
                from datetime import datetime
                end_date_parsed = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Formato de fecha inválido. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            response = ClassExportService.export_cancellation_statistics(
                period_months=period_months,
                instructor_id=instructor_id_parsed,
                start_date=start_date_parsed,
                end_date=end_date_parsed,
                format=format_type
            )
            return response
        except Exception as e:
            logger.error(f"Error al exportar estadísticas de cancelaciones: {str(e)}")
            return Response(
                {'error': 'Error al generar el reporte.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
