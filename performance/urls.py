from django.urls import path
from .views import PerformanceStatisticsView, BeltExamView, EventParticipationView, DisciplineListView

urlpatterns = [
    path('', PerformanceStatisticsView.as_view(), name='performance-statistics'),
    path('belt-exams/', BeltExamView.as_view(), name='belt-exams'),
    path('event-participations/', EventParticipationView.as_view(), name='event-participations'),
    path('disciplines/', DisciplineListView.as_view(), name='discipline-list'),
]