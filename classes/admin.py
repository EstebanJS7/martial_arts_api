from django.contrib import admin
from .models import Class, UserClassReservation, ClassAttendance, ClassTemplate

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'instructor', 'date', 'class_type', 'difficulty_level', 'max_students', 'reservation_count', 'is_cancelled', 'location')
    search_fields = ('name', 'instructor__email', 'location', 'description')
    list_filter = ('date', 'instructor', 'class_type', 'difficulty_level', 'is_cancelled')
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'instructor', 'date', 'duration', 'max_students')
        }),
        ('Clasificación', {
            'fields': ('class_type', 'difficulty_level', 'location')
        }),
        ('Detalles Adicionales', {
            'fields': ('equipment_needed', 'notes')
        }),
        ('Cancelación', {
            'fields': ('is_cancelled', 'cancellation_reason', 'cancelled_by', 'cancelled_at'),
            'classes': ('collapse',)
        }),
        ('Estadísticas', {
            'fields': ('reservation_count', 'attendance_count', 'no_show_count'),
            'classes': ('collapse',)
        }),
    )

@admin.register(UserClassReservation)
class UserClassReservationAdmin(admin.ModelAdmin):
    list_display = ('user', 'class_reserved', 'created_at', 'is_cancelled')
    search_fields = ('user__email', 'class_reserved__name')
    list_filter = ('is_cancelled', 'created_at')

@admin.register(ClassAttendance)
class ClassAttendanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'class_reserved', 'attended', 'check_in_time', 'marked_by')
    search_fields = ('user__email', 'class_reserved__name', 'marked_by__email')
    list_filter = ('attended', 'check_in_time', 'created_at')

@admin.register(ClassTemplate)
class ClassTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'instructor', 'class_type', 'difficulty_level', 'is_active')
    search_fields = ('name', 'instructor__email')
    list_filter = ('class_type', 'difficulty_level', 'is_active')