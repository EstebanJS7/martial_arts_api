# urls.py
from django.urls import path
from .views import (
    EvaluationParameterListCreateView,
    EvaluationParameterDetailView,
    ExamSessionListCreateView,
    ExamSessionDetailView,
    ExamResultListCreateView,
    ExamResultDetailView,
    MyExamResultsView,
    PerformanceStatisticsView,
    UserPerformanceStatsView,
    EventParticipationListView, # Agregar la vista para eventos
)

urlpatterns = [
    # Endpoints para parámetros de evaluación
    path('parameters/', EvaluationParameterListCreateView.as_view(), name='evaluationparameter-list-create'),
    path('parameters/<int:pk>/', EvaluationParameterDetailView.as_view(), name='evaluationparameter-detail'),

    # Endpoints para sesiones de examen
    path('exam-sessions/', ExamSessionListCreateView.as_view(), name='exam-session-list-create'),
    path('exam-sessions/<int:pk>/', ExamSessionDetailView.as_view(), name='exam-session-detail'),

    # Endpoints para resultados de examen (calificación)
    path('exam-results/', ExamResultListCreateView.as_view(), name='exam-result-list-create'),
    path('exam-results/<int:pk>/', ExamResultDetailView.as_view(), name='exam-result-detail'),

    # Endpoint para que el estudiante consulte sus resultados
    path('my-exam-results/', MyExamResultsView.as_view(), name='my-exam-results'),

    # Endpoint para estadísticas de desempeño
    path('statistics/', PerformanceStatisticsView.as_view(), name='performance-statistics'),
    
    # Endpoint para estadísticas de desempeño del usuario
    path('user-stats/', UserPerformanceStatsView.as_view(), name='user-performance-stats'),

    # Endpoint para eventos de desempeño
    path('events/', EventParticipationListView.as_view(), name='event-participation-list'),
]
