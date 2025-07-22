# views.py
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Prefetch, Q
from .models import (
    EvaluationParameter,
    ExamSession,
    ExamResult,
    PerformanceStatistics,
    Discipline,
    EventParticipation # Importar modelo de eventos
)
from .serializers import (
    EvaluationParameterSerializer,
    ExamSessionSerializer,
    ExamResultSerializer,
    PerformanceStatisticsSerializer,
    EventParticipationSerializer # Importar el serializer
)
from users.permissions import IsAdminUser, IsInstructorUser  # Se asume que existen
from martial_arts_api.pagination import StandardResultsSetPagination, SmallResultsSetPagination
from django.utils import timezone

# --- Endpoints para EvaluationParameter ---

class EvaluationParameterListCreateView(generics.ListCreateAPIView):
    queryset = EvaluationParameter.objects.all().order_by('name')
    serializer_class = EvaluationParameterSerializer
    permission_classes = [IsAdminUser]  # Solo admin puede gestionar parámetros
    pagination_class = SmallResultsSetPagination

class EvaluationParameterDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EvaluationParameter.objects.all()
    serializer_class = EvaluationParameterSerializer
    permission_classes = [IsAdminUser]

# --- Endpoints para ExamSession ---

class ExamSessionListCreateView(generics.ListCreateAPIView):
    """
    Permite a instructores o administradores crear una sesión de examen.
    En la creación, se puede enviar la lista de participantes.
    """
    serializer_class = ExamSessionSerializer
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get_queryset(self):
        # Optimización: Usar select_related para el creador y prefetch_related para participantes
        return ExamSession.objects.select_related('created_by').prefetch_related(
            'participants'
        ).order_by('-exam_date')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class ExamSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExamSessionSerializer
    permission_classes = [IsAdminUser | IsInstructorUser]
    
    def get_queryset(self):
        return ExamSession.objects.select_related('created_by').prefetch_related(
            'participants'
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
        
        # Obtener el nivel de habilidad del usuario
        try:
            skill_level = user.userprofile.skill_level
        except:
            skill_level = "Principiante"
        
        # Obtener estadísticas de asistencia
        # Suponemos que hay un modelo que registra la asistencia a clases
        from classes.models import UserClassReservation
        
        # Total de clases a las que ha asistido
        attended_classes = UserClassReservation.objects.filter(
            user=user,
            is_cancelled=False,
            class_reserved__date__lt=timezone.now().date()
        ).count()
        
        # Total de clases programadas en el pasado
        from classes.models import Class
        total_classes = UserClassReservation.objects.filter(
            user=user,
            class_reserved__date__lt=timezone.now().date()
        ).count()
        
        # Calcular tasa de asistencia
        attendance_rate = 0
        if total_classes > 0:
            attendance_rate = (attended_classes / total_classes) * 100
        
        # Obtener logros del usuario
        achievements = []
        user_exam_results = ExamResult.objects.filter(participant=user).order_by('-exam_session__exam_date')
        
        for result in user_exam_results[:3]:  # Mostrar solo los 3 más recientes
            achievements.append({
                'id': result.id,
                'title': f"Examen de {result.exam_session.title}",
                'description': f"Calificación: {result.final_score}/100",
                'dateEarned': result.exam_session.date.strftime('%Y-%m-%d'),
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
                        score = ParameterScore.objects.get(
                            exam_result=latest_result,
                            parameter=param
                        ).score
                        parameter_scores.append(score)
                        max_level = max(max_level, 5)  # Suponemos que el nivel máximo es 5
                    except ParameterScore.DoesNotExist:
                        pass
                
                if parameter_scores:
                    avg_score = sum(parameter_scores) / len(parameter_scores)
                    level = int(avg_score / 20)  # Convertir puntuación (0-100) a nivel (0-5)
                    
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

class EventParticipationListView(generics.ListAPIView):
    """
    Lista las participaciones en eventos del usuario autenticado.
    """
    serializer_class = EventParticipationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EventParticipation.objects.filter(user=self.request.user).order_by('-event_date')
