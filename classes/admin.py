from django.contrib import admin
from .models import Class, UserClassReservation, ClassAttendance, ClassTemplate

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'instructor', 'date', 'max_students', 'reservation_count')
    search_fields = ('name', 'instructor__email')
    list_filter = ('date', 'instructor')

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