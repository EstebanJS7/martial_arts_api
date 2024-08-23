from rest_framework import generics
from .models import PerformanceStatistics, BeltExam, EventParticipation, Discipline
from .serializers import PerformanceStatisticsSerializer, BeltExamSerializer, EventParticipationSerializer, DisciplineSerializer

class PerformanceStatisticsView(generics.ListCreateAPIView):
    queryset = PerformanceStatistics.objects.all()
    serializer_class = PerformanceStatisticsSerializer

class BeltExamView(generics.ListCreateAPIView):
    queryset = BeltExam.objects.all()
    serializer_class = BeltExamSerializer

class EventParticipationView(generics.ListCreateAPIView):
    queryset = EventParticipation.objects.all()
    serializer_class = EventParticipationSerializer

class DisciplineListView(generics.ListCreateAPIView):
    queryset = Discipline.objects.all()
    serializer_class = DisciplineSerializer