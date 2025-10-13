from django.contrib import admin
from .models import (
    Discipline, 
    EvaluationParameter, 
    ExamSession, 
    ExamResult, 
    ExamResultParameterScore, 
    EventCategory,
    Event,
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

@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'event_date', 'location', 'organizer', 'is_verified', 'created_by')
    list_filter = ('is_verified', 'event_date', 'created_by', 'categories')
    search_fields = ('name', 'location', 'organizer', 'created_by__email')
    readonly_fields = ('created_at', 'verified_at', 'created_by', 'verified_by')
    filter_horizontal = ('categories', 'disciplines')

@admin.register(EventParticipation)
class EventParticipationAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'event_category', 'result', 'is_verified', 'created_at')
    list_filter = ('result', 'is_verified', 'created_at', 'event_category')
    search_fields = ('user__email', 'event__name', 'event_category__name')
    readonly_fields = ('created_at', 'verified_at', 'verified_by')

@admin.register(PerformanceStatistics)
class PerformanceStatisticsAdmin(admin.ModelAdmin):
    list_display = ('user', 'classes_attended', 'last_updated')
    search_fields = ('user__email',)
