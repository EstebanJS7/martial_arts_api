from django.contrib import admin
from .models import (
    Discipline, 
    EvaluationParameter, 
    ExamSession, 
    ExamResult, 
    ExamResultParameterScore, 
    EventParticipation, 
    PerformanceStatistics
)

@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(EvaluationParameter)
class EvaluationParameterAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ('belt_level', 'exam_date', 'created_by')
    list_filter = ('belt_level', 'exam_date')
    search_fields = ('created_by__email', 'belt_level')

@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('exam_session', 'participant', 'graded')
    list_filter = ('graded',)
    search_fields = ('participant__email', 'exam_session__belt_level')

@admin.register(ExamResultParameterScore)
class ExamResultParameterScoreAdmin(admin.ModelAdmin):
    list_display = ('exam_result', 'parameter', 'score')
    search_fields = ('exam_result__participant__email', 'parameter__name')

@admin.register(EventParticipation)
class EventParticipationAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_name', 'category', 'event_date')
    list_filter = ('category', 'event_date')
    search_fields = ('user__email', 'event_name')

@admin.register(PerformanceStatistics)
class PerformanceStatisticsAdmin(admin.ModelAdmin):
    list_display = ('user', 'classes_attended', 'last_updated')
    search_fields = ('user__email',)
