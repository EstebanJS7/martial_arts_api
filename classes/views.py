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

from .models import Class, UserClassReservation
from .serializers import (
    ClassSerializer, 
    UserClassReservationSerializer, 
    MultiClassCreateSerializer,
    MultiClassUpdateSerializer
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
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Obtener la fecha actual
        now = timezone.now()
        
        # Obtener las clases que ocurrirán en los próximos 7 días
        end_date = now + timedelta(days=7)
        
        # Filtrar las clases por fecha
        upcoming_classes = Class.objects.filter(
            date__gte=now.date(),
            date__lte=end_date.date()
        ).order_by('date', 'start_time')
        
        # Verificar si el usuario tiene reservas para estas clases
        user_reservations = UserClassReservation.objects.filter(
            user=request.user,
            class_instance__in=upcoming_classes,
            is_cancelled=False
        ).values_list('class_instance_id', flat=True)
        
        # Serializar las clases
        serializer = ClassSerializer(upcoming_classes, many=True)
        
        # Agregar información de reserva a cada clase
        data = serializer.data
        for class_data in data:
            class_data['is_reserved'] = class_data['id'] in user_reservations
            
            # Calcular espacios disponibles
            total_capacity = class_data.get('capacity', 0)
            reservations_count = UserClassReservation.objects.filter(
                class_instance_id=class_data['id'],
                is_cancelled=False
            ).count()
            class_data['available_spots'] = max(0, total_capacity - reservations_count)
        
        return Response(data)
