from django.contrib import admin
from .models import Discipline, EvaluationParameter, BeltExam, ExamParameterScore, EventParticipation, PerformanceStatistics

@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(EvaluationParameter)
class EvaluationParameterAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(BeltExam)
class BeltExamAdmin(admin.ModelAdmin):
    list_display = ('user', 'belt_level', 'exam_date', 'passed')
    list_filter = ('passed', 'belt_level')
    search_fields = ('user__email',)

@admin.register(ExamParameterScore)
class ExamParameterScoreAdmin(admin.ModelAdmin):
    list_display = ('exam', 'parameter', 'score')
    search_fields = ('exam__user__email', 'parameter__name')

@admin.register(EventParticipation)
class EventParticipationAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_name', 'category', 'event_date')
    list_filter = ('category', 'event_date')
    search_fields = ('user__email', 'event_name')

@admin.register(PerformanceStatistics)
class PerformanceStatisticsAdmin(admin.ModelAdmin):
    list_display = ('user', 'classes_attended', 'last_updated')
    search_fields = ('user__email',)
