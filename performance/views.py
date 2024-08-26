from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import PerformanceStatistics, BeltExam, EventParticipation, EvaluationParameter, ExamParameterScore
from .serializers import (PerformanceStatisticsSerializer, BeltExamSerializer, 
                          EventParticipationSerializer, EvaluationParameterSerializer, ExamParameterScoreSerializer)

# Vistas para los parámetros de evaluación
class EvaluationParameterListCreateView(generics.ListCreateAPIView):
    queryset = EvaluationParameter.objects.all()
    serializer_class = EvaluationParameterSerializer
    permission_classes = [IsAdminUser]

class EvaluationParameterDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EvaluationParameter.objects.all()
    serializer_class = EvaluationParameterSerializer
    permission_classes = [IsAdminUser]

# Vistas para los exámenes de cinturón
class BeltExamListCreateView(generics.ListCreateAPIView):
    queryset = BeltExam.objects.all()
    serializer_class = BeltExamSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class BeltExamDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BeltExam.objects.all()
    serializer_class = BeltExamSerializer
    permission_classes = [IsAuthenticated]

# Vistas para las participaciones en eventos
class EventParticipationListCreateView(generics.ListCreateAPIView):
    queryset = EventParticipation.objects.all()
    serializer_class = EventParticipationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class EventParticipationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EventParticipation.objects.all()
    serializer_class = EventParticipationSerializer
    permission_classes = [IsAuthenticated]

# Vistas para las puntuaciones de los parámetros evaluados
class ExamParameterScoreListCreateView(generics.ListCreateAPIView):
    queryset = ExamParameterScore.objects.all()
    serializer_class = ExamParameterScoreSerializer
    permission_classes = [IsAdminUser]

class ExamParameterScoreDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ExamParameterScore.objects.all()
    serializer_class = ExamParameterScoreSerializer
    permission_classes = [IsAdminUser]

# Vista para las estadísticas de desempeño
class PerformanceStatisticsView(generics.RetrieveAPIView):
    queryset = PerformanceStatistics.objects.all()
    serializer_class = PerformanceStatisticsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PerformanceStatistics.objects.filter(user=self.request.user)
