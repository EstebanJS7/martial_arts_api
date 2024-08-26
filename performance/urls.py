from django.urls import path
from .views import (PerformanceStatisticsView, BeltExamListCreateView, BeltExamDetailView, 
                    EventParticipationListCreateView, EventParticipationDetailView, 
                    EvaluationParameterListCreateView, EvaluationParameterDetailView,
                    ExamParameterScoreListCreateView, ExamParameterScoreDetailView)

urlpatterns = [
    path('statistics/', PerformanceStatisticsView.as_view(), name='performance-statistics'),
    path('exams/', BeltExamListCreateView.as_view(), name='beltexam-list-create'),
    path('exams/<int:pk>/', BeltExamDetailView.as_view(), name='beltexam-detail'),
    path('events/', EventParticipationListCreateView.as_view(), name='eventparticipation-list-create'),
    path('events/<int:pk>/', EventParticipationDetailView.as_view(), name='eventparticipation-detail'),
    path('parameters/', EvaluationParameterListCreateView.as_view(), name='evaluationparameter-list-create'),
    path('parameters/<int:pk>/', EvaluationParameterDetailView.as_view(), name='evaluationparameter-detail'),
    path('scores/', ExamParameterScoreListCreateView.as_view(), name='examparameterscore-list-create'),
    path('scores/<int:pk>/', ExamParameterScoreDetailView.as_view(), name='examparameterscore-detail'),
]
