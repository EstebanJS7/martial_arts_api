from django.db import models
from django.conf import settings
from datetime import timedelta

class Class(models.Model):
    """
    Modelo para representar una clase (sesión) de artes marciales.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='instructed_classes'
    )
    date = models.DateTimeField()
    max_students = models.IntegerField()
    # Nuevo campo duración con valor por defecto de 1 hora
    duration = models.DurationField(default=timedelta(hours=1))
    # Campo para almacenar el número de reservas actuales y evitar consultas COUNT cada vez
    reservation_count = models.IntegerField(default=0)

    class Meta: 
        verbose_name = "Clase"
        verbose_name_plural = "Clases"

    def __str__(self):
        return self.name

class UserClassReservation(models.Model):
    """
    Modelo para las reservas de clases realizadas por los usuarios.
    La combinación (user, class_reserved) es única.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    class_reserved = models.ForeignKey(Class, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_cancelled = models.BooleanField(default=False)  # Nuevo campo para cancelar reservas

    class Meta:
        unique_together = ('user', 'class_reserved')
        verbose_name = "Reserva de clase"
        verbose_name_plural = "Reservas de clases"

    def __str__(self):
        return f'{self.user.email} - {self.class_reserved.name}'


class ClassAttendance(models.Model):
    """
    Modelo para registrar la asistencia de estudiantes a clases.
    Permite registrar si un estudiante asistió o no a una clase.
    """
    class_reserved = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='attendances')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='class_attendances')
    attended = models.BooleanField(default=False)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendances',
        help_text='Usuario que marcó la asistencia (instructor/admin)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('class_reserved', 'user')
        verbose_name = "Asistencia de clase"
        verbose_name_plural = "Asistencias de clases"
        indexes = [
            models.Index(fields=['class_reserved', 'attended']),
            models.Index(fields=['user', 'attended']),
        ]

    def __str__(self):
        status = "Presente" if self.attended else "Ausente"
        return f'{self.user.email} - {self.class_reserved.name} ({status})'


class ClassTemplate(models.Model):
    """
    Plantilla para crear clases recurrentes de forma rápida.
    Permite reutilizar configuraciones comunes de clases.
    """
    CLASS_TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('intensive', 'Intensiva'),
        ('private', 'Privada'),
        ('seminar', 'Seminario'),
        ('exam', 'Examen'),
    ]

    DIFFICULTY_LEVEL_CHOICES = [
        ('beginner', 'Principiante'),
        ('intermediate', 'Intermedio'),
        ('advanced', 'Avanzado'),
        ('all_levels', 'Todos los niveles'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='class_templates'
    )
    class_type = models.CharField(max_length=50, choices=CLASS_TYPE_CHOICES, default='regular')
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_LEVEL_CHOICES, default='all_levels')
    duration = models.DurationField(default=timedelta(hours=1))
    max_students = models.IntegerField(default=20)
    location = models.CharField(max_length=200, blank=True)
    equipment_needed = models.TextField(blank=True)
    prerequisites = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plantilla de clase"
        verbose_name_plural = "Plantillas de clases"

    def __str__(self):
        return f'{self.name} ({self.get_class_type_display()})'
