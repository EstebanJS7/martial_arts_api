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
    Discipline
)
from .serializers import (
    EvaluationParameterSerializer,
    ExamSessionSerializer,
    ExamResultSerializer,
    PerformanceStatisticsSerializer
)
from users.permissions import IsAdminUser, IsInstructorUser  # Se asume que existen
from martial_arts_api.pagination import StandardResultsSetPagination, SmallResultsSetPagination

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
