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

from .models import Class, UserClassReservation, ClassAttendance, ClassTemplate
from .services import ClassDashboardService
from .serializers import (
    ClassSerializer, 
    UserClassReservationSerializer, 
    MultiClassCreateSerializer,
    MultiClassUpdateSerializer,
    ClassAttendanceSerializer,
    ClassAttendanceCreateSerializer,
    ClassTemplateSerializer,
)
from users.permissions import IsAdminUser, IsInstructorUser
from rest_framework.permissions import IsAuthenticated

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
            
        # Incrementar el contador de reservas y guardar
        class_obj.reservation_count = F('reservation_count') + 1
        class_obj.save()
        
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

class UpcomingClassesView(APIView):
    """
    Vista para obtener las próximas clases programadas para el usuario autenticado.
    Muestra clases de los próximos 30 días con información completa del instructor.
    """
    permission_classes = [IsAuthenticated]
    
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
        
        # Serializar las clases con el contexto para el request
        serializer = ClassSerializer(upcoming_classes, many=True, context={'request': request})
        
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
