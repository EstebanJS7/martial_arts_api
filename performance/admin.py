from django.contrib import admin
from .models import Discipline, EvaluationParameter, BeltExam, EventParticipation, PerformanceStatistics, ExamParameterScore

admin.site.register(Discipline)
admin.site.register(EvaluationParameter)
admin.site.register(BeltExam)
admin.site.register(ExamParameterScore)
admin.site.register(EventParticipation)
admin.site.register(PerformanceStatistics)