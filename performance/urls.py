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
    EventCategoryListCreateView,
    EventCategoryDetailView,
    EventListCreateView,
    EventDetailView,
    EventVerifyView,
    VerifiedEventsView,
    EventParticipationListCreateView,
    EventParticipationDetailView,
    EventParticipationVerifyView,
    MyEventParticipationsView,
    MyProgressView,
    AtRiskStudentsView,
    ExamEligibleStudentsView,
)
from .belt_rank_views import BeltRankListView, BeltRankDetailView

urlpatterns = [
    # Endpoints para cinturones
    path('belt-ranks/', BeltRankListView.as_view(), name='belt-rank-list'),
    path('belt-ranks/<int:pk>/', BeltRankDetailView.as_view(), name='belt-rank-detail'),
    
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

    # Endpoints de retención y progreso
    path('my-progress/', MyProgressView.as_view(), name='my-progress'),
    path('at-risk/', AtRiskStudentsView.as_view(), name='at-risk'),
    path('exam-eligible/', ExamEligibleStudentsView.as_view(), name='exam-eligible'),

    # Endpoints para categorías de eventos (nuevo sistema dinámico)
    path('event-categories/', EventCategoryListCreateView.as_view(), name='event-category-list-create'),
    path('event-categories/<int:pk>/', EventCategoryDetailView.as_view(), name='event-category-detail'),
    
    # Endpoints para eventos (nuevo sistema)
    path('events/', EventListCreateView.as_view(), name='event-list-create'),
    path('events/<int:pk>/', EventDetailView.as_view(), name='event-detail'),
    path('events/<int:pk>/verify/', EventVerifyView.as_view(), name='event-verify'),
    path('events/verified/', VerifiedEventsView.as_view(), name='verified-events'),
    
    # Endpoints para participaciones en eventos (actualizado)
    path('participations/', EventParticipationListCreateView.as_view(), name='event-participation-list-create'),
    path('participations/<int:pk>/', EventParticipationDetailView.as_view(), name='event-participation-detail'),
    path('participations/<int:pk>/verify/', EventParticipationVerifyView.as_view(), name='event-participation-verify'),
    path('my-participations/', MyEventParticipationsView.as_view(), name='my-event-participations'),
]
