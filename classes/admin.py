from django.contrib import admin
from .models import Class, UserClassReservation

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'instructor', 'date', 'max_students')
    search_fields = ('name', 'instructor__email')

@admin.register(UserClassReservation)
class UserClassReservationAdmin(admin.ModelAdmin):
    list_display = ('user', 'class_reserved', 'created_at')
    search_fields = ('user__email', 'class_reserved__name')