# views.py
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Prefetch, Q
from .models import (
    EvaluationParameter,
    ExamSession,
    ExamResult,
    ExamResultParameterScore,
    PerformanceStatistics,
    Discipline,
    EventCategory,
    Event,
    EventParticipation
)
from .serializers import (
    EvaluationParameterSerializer,
    ExamSessionSerializer,
    ExamResultSerializer,
    PerformanceStatisticsSerializer,
    EventCategorySerializer,
    EventSerializer,
    EventParticipationSerializer
)
from users.permissions import IsAdminUser, IsInstructorUser  # Se asume que existen
from martial_arts_api.pagination import StandardResultsSetPagination, SmallResultsSetPagination
from django.utils import timezone

# --- Endpoints para EvaluationParameter ---

class EvaluationParameterListCreateView(generics.ListCreateAPIView):
    queryset = EvaluationParameter.objects.all().order_by('name')
    serializer_class = EvaluationParameterSerializer
    permission_classes = [IsAdminUser | IsInstructorUser]  # Admin e instructores pueden gestionar parámetros
    pagination_class = SmallResultsSetPagination

class EvaluationParameterDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EvaluationParameter.objects.all()
    serializer_class = EvaluationParameterSerializer
    permission_classes = [IsAdminUser | IsInstructorUser]

# --- Endpoints para ExamSession ---

class ExamSessionListCreateView(generics.ListCreateAPIView):
    """
    Permite a instructores o administradores crear una sesión de examen.
    En la creación, se puede enviar la lista de participantes.
    """
    serializer_class = ExamSessionSerializer
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get_queryset(self):
        # Optimización: Usar select_related para el creador y prefetch_related para participantes y parámetros
        return ExamSession.objects.select_related('created_by', 'belt_rank').prefetch_related(
            'participants', 'evaluation_parameters'
        ).order_by('-exam_date')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class ExamSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExamSessionSerializer
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get_queryset(self):
        return ExamSession.objects.select_related('created_by', 'belt_rank').prefetch_related(
            'participants', 'evaluation_parameters'
        )

# --- Endpoints para ExamResult ---

class ExamResultListCreateView(generics.ListCreateAPIView):
    """
    Permite a instructores/admin ver o crear resultados de examen.
    Se puede usar para calificar a los participantes.
    """
    serializer_class = ExamResultSerializer
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get_queryset(self):
        # Filtrar por sesión de examen si se proporciona
        exam_session_id = self.request.query_params.get('exam_session')
        queryset = ExamResult.objects.select_related(
            'exam_session', 'participant'
        )
        
        if exam_session_id:
            queryset = queryset.filter(exam_session_id=exam_session_id)
            
        return queryset.order_by('-exam_session__exam_date')

    def perform_create(self, serializer):
        serializer.save()

class ExamResultDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExamResultSerializer
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get_queryset(self):
        return ExamResult.objects.select_related('exam_session', 'participant')

class MyExamResultsView(generics.ListAPIView):
    """
    Permite a un estudiante ver sus resultados de examen.
    """
    serializer_class = ExamResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Optimización: Usar select_related para cargar la sesión de examen
        return ExamResult.objects.select_related(
            'exam_session'
        ).filter(
            participant=self.request.user
        ).order_by('-exam_session__exam_date')

class PerformanceStatisticsView(generics.RetrieveAPIView):
    """
    Permite al usuario autenticado ver sus estadísticas de desempeño.
    """
    serializer_class = PerformanceStatisticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Optimización: Usar select_related para cargar el usuario
        return PerformanceStatistics.objects.select_related('user').filter(
            user=self.request.user
        )

class UserPerformanceStatsView(APIView):
    """
    Vista para obtener las estadísticas de desempeño del usuario autenticado.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Calcular el nivel de habilidad basándose en el cinturón del usuario
        skill_level = "Principiante"
        try:
            user_profile = user.userprofile
            belt_rank_name = user_profile.belt_rank
            
            if belt_rank_name:
                # Buscar el cinturón en el modelo BeltRank
                try:
                    from .models import BeltRank
                    belt_rank = BeltRank.objects.get(name=belt_rank_name, is_active=True)
                    
                    # Determinar nivel de habilidad basado en la categoría y orden del cinturón
                    if belt_rank.category == 'Dan':
                        # Para cinturones Dan, usar el número del Dan
                        if '1°' in belt_rank_name or '1er' in belt_rank_name or '1' in belt_rank_name:
                            skill_level = "Avanzado"
                        elif '2°' in belt_rank_name or '2do' in belt_rank_name or '2' in belt_rank_name:
                            skill_level = "Experto"
                        elif '3°' in belt_rank_name or '3er' in belt_rank_name or '3' in belt_rank_name:
                            skill_level = "Maestro"
                        elif belt_rank.order_number >= 16:  # 4° Dan o superior
                            skill_level = "Gran Maestro"
                        else:
                            skill_level = "Avanzado"
                    elif belt_rank.category == 'Kyu B':
                        # Cinturones Kyu B son intermedios
                        skill_level = "Intermedio"
                    else:
                        # Cinturones Kyu A son principiantes
                        skill_level = "Principiante"
                except BeltRank.DoesNotExist:
                    # Si el cinturón no existe en el sistema, usar el nombre del cinturón como nivel
                    if 'Negro' in belt_rank_name or 'Dan' in belt_rank_name:
                        skill_level = "Avanzado"
                    elif any(color in belt_rank_name for color in ['Azul', 'Marrón', 'Rojo']):
                        skill_level = "Intermedio"
                    else:
                        skill_level = "Principiante"
        except Exception:
            skill_level = "Principiante"
        
        # Estadísticas de asistencia basadas en registros reales de asistencia
        # (ClassAttendance), no en reservas: tener una reserva no implica haber
        # asistido.
        from classes.models import Class, ClassAttendance

        now = timezone.now()

        # Clases realmente asistidas: registros marcados como presente por el
        # instructor, en clases pasadas y no canceladas.
        attended_classes = ClassAttendance.objects.filter(
            user=user,
            attended=True,
            class_reserved__is_cancelled=False,
            class_reserved__date__lt=now,
        ).count()

        # Total de clases relevantes: clases pasadas no canceladas donde el
        # estudiante tenía una reserva activa O tiene registro de asistencia
        # (reservó => se esperaba su asistencia; el registro puede faltar si el
        # instructor no cargó la lista, pero la clase igualmente evaluable).
        total_classes = Class.objects.filter(
            is_cancelled=False,
            date__lt=now,
        ).filter(
            Q(userclassreservation__user=user, userclassreservation__is_cancelled=False)
            | Q(attendances__user=user)
        ).distinct().count()
        
        # Calcular tasa de asistencia (protegida contra división por cero)
        attendance_rate = 0
        if total_classes > 0:
            attendance_rate = (attended_classes / total_classes) * 100
        
        # Obtener logros del usuario
        achievements = []
        user_exam_results = ExamResult.objects.filter(participant=user).order_by('-exam_session__exam_date')
        
        for result in user_exam_results[:3]:  # Mostrar solo los 3 más recientes
            # Calcular puntuación promedio si hay calificaciones
            avg_score = 0
            if result.parameter_scores.exists():
                total_score = sum(score.score for score in result.parameter_scores.all())
                avg_score = total_score / result.parameter_scores.count()
            
            achievements.append({
                'id': result.id,
                'title': f"Examen de {result.exam_session.belt_level}",
                'description': f"Calificación: {avg_score:.1f}/10" if result.graded else "Pendiente de calificación",
                'dateEarned': result.exam_session.exam_date.strftime('%Y-%m-%d'),
                'icon': 'trophy'  # Icono por defecto
            })
        
        # Obtener progreso por categoría
        progress_categories = []
        
        # Obtener parámetros de evaluación agrupados por categoría
        categories = EvaluationParameter.objects.values_list('category', flat=True).distinct()
        
        for category in categories:
            # Obtener el último resultado de examen para esta categoría
            parameters = EvaluationParameter.objects.filter(category=category)
            
            if parameters.exists() and user_exam_results.exists():
                latest_result = user_exam_results.first()
                
                # Calcular el promedio de puntuación para esta categoría
                parameter_scores = []
                max_level = 0
                
                for param in parameters:
                    try:
                        score = ExamResultParameterScore.objects.get(
                            exam_result=latest_result,
                            parameter=param
                        ).score
                        parameter_scores.append(score)
                        max_level = max(max_level, 10)  # Nivel máximo es 10
                    except ExamResultParameterScore.DoesNotExist:
                        pass
                
                if parameter_scores:
                    avg_score = sum(parameter_scores) / len(parameter_scores)
                    level = int(avg_score / 2)  # Convertir puntuación (0-10) a nivel (0-5)
                    
                    progress_categories.append({
                        'category': category,
                        'level': level,
                        'maxLevel': max_level,
                        'percentage': avg_score
                    })
        
        # Construir respuesta
        response_data = {
            'attendedClasses': attended_classes,
            'totalClasses': total_classes,
            'attendanceRate': round(attendance_rate, 2),
            'skillLevel': skill_level,
            'achievements': achievements,
            'progressByCategory': progress_categories
        }
        
        return Response(response_data)

# --- Endpoints para Event (nuevo sistema) ---

class EventListCreateView(generics.ListCreateAPIView):
    """
    Lista todos los eventos o crea un nuevo evento.
    - GET: Lista eventos (todos para admin/instructor, solo verificados para estudiantes)
    - POST: Crea un nuevo evento (solo admin/instructor)
    """
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        # La autorización de escritura vive en permission_classes (los retornos de
        # perform_* son ignorados por DRF y nunca bloquean nada).
        # En generics clásicos no existe self.action; se discrimina por método HTTP.
        if self.request.method == 'POST':
            return [(IsAdminUser | IsInstructorUser)()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'userprofile') and user.userprofile.role in ['admin', 'instructor']:
            # Admin e instructores ven todos los eventos
            return Event.objects.all().order_by('-created_at')
        else:
            # Estudiantes solo ven eventos verificados
            return Event.objects.filter(is_verified=True).order_by('-event_date')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Obtiene, actualiza o elimina un evento específico.
    GET abierto a autenticados (estudiantes solo ven verificados);
    PUT/PATCH/DELETE restringidos a admin/instructores.
    """
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        # En generics clásicos no existe self.action; se discrimina por método HTTP
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [(IsAdminUser | IsInstructorUser)()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'userprofile') and user.userprofile.role in ['admin', 'instructor']:
            return Event.objects.all()
        else:
            return Event.objects.filter(is_verified=True)

class EventVerifyView(APIView):
    """
    Verifica un evento (solo admin).
    """
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            event = Event.objects.get(pk=pk)
            if event.is_verified:
                return Response(
                    {'error': 'El evento ya está verificado'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            event.is_verified = True
            event.verified_by = request.user
            event.verified_at = timezone.now()
            event.save()
            
            serializer = EventSerializer(event)
            return Response(serializer.data)
        except Event.DoesNotExist:
            return Response(
                {'error': 'Evento no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class VerifiedEventsView(generics.ListAPIView):
    """
    Lista solo los eventos verificados (para estudiantes).
    """
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Event.objects.filter(is_verified=True).order_by('-event_date')

# --- Endpoints para EventParticipation (actualizado) ---

class EventParticipationListCreateView(generics.ListCreateAPIView):
    """
    Lista participaciones en eventos o crea una nueva participación.
    - GET: Lista participaciones (todas para admin/instructor, solo propias para estudiantes)
    - POST: Crea una nueva participación
    """
    serializer_class = EventParticipationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'userprofile') and user.userprofile.role in ['admin', 'instructor']:
            # Admin e instructores ven todas las participaciones
            return EventParticipation.objects.all().order_by('-created_at')
        else:
            # Estudiantes solo ven sus propias participaciones
            return EventParticipation.objects.filter(user=user).order_by('-created_at')

    def perform_create(self, serializer):
        # DRF ignora los valores retornados por perform_create: para bloquear la
        # creación hay que lanzar ValidationError.
        # Verificar que el evento esté verificado
        event_id = self.request.data.get('event')
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            raise ValidationError({'error': 'Evento no encontrado'})
        if not event.is_verified:
            raise ValidationError({'error': 'Solo puedes participar en eventos verificados'})

        serializer.save(user=self.request.user)

class EventParticipationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Obtiene, actualiza o elimina una participación específica.
    """
    serializer_class = EventParticipationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'userprofile') and user.userprofile.role in ['admin', 'instructor']:
            return EventParticipation.objects.all()
        else:
            return EventParticipation.objects.filter(user=user)

class EventParticipationVerifyView(APIView):
    """
    Verifica una participación en evento (solo admin).
    """
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            participation = EventParticipation.objects.get(pk=pk)
            if participation.is_verified:
                return Response(
                    {'error': 'La participación ya está verificada'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            participation.is_verified = True
            participation.verified_by = request.user
            participation.verified_at = timezone.now()
            participation.save()
            
            serializer = EventParticipationSerializer(participation)
            return Response(serializer.data)
        except EventParticipation.DoesNotExist:
            return Response(
                {'error': 'Participación no encontrada'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class MyEventParticipationsView(generics.ListAPIView):
    """
    Lista las participaciones en eventos del usuario autenticado.
    """
    serializer_class = EventParticipationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        print(f"🔍 MyEventParticipationsView - User: {user.id} ({user.email})")
        
        # Obtener todas las participaciones para debug
        all_participations = EventParticipation.objects.all()
        print(f"🔍 Total participations in DB: {all_participations.count()}")
        
        # Obtener participaciones del usuario
        user_participations = EventParticipation.objects.filter(user=user)
        print(f"🔍 User participations: {user_participations.count()}")
        
        # Debug: mostrar detalles de las participaciones
        for participation in all_participations:
            print(f"🔍 Participation {participation.id}: user={participation.user.id} ({participation.user.email}), event={participation.event.name}")
        
        return user_participations.order_by('-created_at')

# --- Endpoints para EventCategory (nuevo sistema dinámico) ---

class EventCategoryListCreateView(generics.ListCreateAPIView):
    """
    Lista todas las categorías de eventos o crea una nueva categoría.
    - GET: Lista categorías activas
    - POST: Crea una nueva categoría (solo admin/instructor)
    """
    serializer_class = EventCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        # POST (crear categoría) restringido a admin/instructores vía permission_classes;
        # en generics clásicos no existe self.action, se discrimina por método HTTP
        if self.request.method == 'POST':
            return [(IsAdminUser | IsInstructorUser)()]
        return super().get_permissions()

    def get_queryset(self):
        return EventCategory.objects.filter(is_active=True).order_by('name')

    def perform_create(self, serializer):
        serializer.save()

class EventCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Obtiene, actualiza o elimina una categoría específica.
    GET abierto a autenticados; PUT/PATCH para admin/instructores;
    DELETE solo para admin.
    """
    serializer_class = EventCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        # Autorización por método HTTP: antes se validaba dentro de perform_update/
        # perform_destroy, cuyos retornos DRF ignora (nunca bloqueaban nada)
        if self.request.method == 'DELETE':
            return [IsAdminUser()]
        if self.request.method in ['PUT', 'PATCH']:
            return [(IsAdminUser | IsInstructorUser)()]
        return super().get_permissions()

    def get_queryset(self):
        return EventCategory.objects.all()
