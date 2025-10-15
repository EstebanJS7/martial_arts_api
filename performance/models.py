# models.py
from django.db import models
from django.conf import settings
from datetime import timedelta

# Modelo para representar disciplinas (ya existente en performance)
class Discipline(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

# Modelo para definir los parámetros de evaluación
class EvaluationParameter(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

# --- Flujo de Exámenes ---

class ExamSession(models.Model):
    """
    Representa una sesión de examen, donde se define:
      - El nivel de cinturón a evaluar.
      - La fecha del examen.
      - La lista de participantes (estudiantes).
      - El instructor o administrador que organiza la sesión.
      - Los parámetros de evaluación a calificar.
    """
    belt_level = models.CharField(max_length=50)  # Ej: "Black Belt"
    exam_date = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_exam_sessions'
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='exam_sessions'
    )
    evaluation_parameters = models.ManyToManyField(
        EvaluationParameter,
        related_name='exam_sessions',
        blank=True,
        help_text="Parámetros de evaluación que se calificarán en esta sesión"
    )

    class Meta:
        ordering = ['exam_date']
        verbose_name = "Exam Session"
        verbose_name_plural = "Exam Sessions"

    def __str__(self):
        return f"Exam Session for {self.belt_level} on {self.exam_date}"

class ExamResult(models.Model):
    """
    Representa el resultado de un participante en una sesión de examen.
    Cada participante tendrá un único resultado por sesión.
    """
    exam_session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='exam_results')
    participant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_results')
    graded = models.BooleanField(default=False)  # Indica si ya fue calificado

    class Meta:
        unique_together = ('exam_session', 'participant')
        verbose_name = "Exam Result"
        verbose_name_plural = "Exam Results"

    def __str__(self):
        return f"Result for {self.participant.email} in {self.exam_session}"

class ExamResultParameterScore(models.Model):
    """
    Almacena la puntuación de un parámetro de evaluación para un resultado de examen.
    """
    exam_result = models.ForeignKey(ExamResult, on_delete=models.CASCADE, related_name='parameter_scores')
    parameter = models.ForeignKey(EvaluationParameter, on_delete=models.CASCADE, related_name='exam_result_scores')
    score = models.IntegerField()

    def __str__(self):
        return f"{self.exam_result} - {self.parameter.name}: {self.score}"

# --- Estadísticas de Desempeño (ya existente) ---

class PerformanceStatistics(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    classes_attended = models.IntegerField(default=0)
    belt_exams = models.ManyToManyField(ExamSession, related_name='performance_statistics', blank=True)
    event_participations = models.ManyToManyField('EventParticipation', related_name='performance_statistics', blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Performance Statistic"
        verbose_name_plural = "Performance Statistics"

    def __str__(self):
        return f"Performance stats for {self.user.email}"

    def update_statistics(self):
        """
        Actualiza las estadísticas basadas en reservas de clases, exámenes (ExamSession)
        y participaciones en eventos.
        """
        # Ejemplo: suponiendo que userclassreservation_set provenga de otro módulo.
        self.classes_attended = self.user.userclassreservation_set.count()
        # Para exámenes y eventos se sincroniza la relación many-to-many
        self.belt_exams.set(self.user.exam_sessions.all())
        self.event_participations.set(self.user.event_participations.all())
        self.save()

# Modelo para categorías de eventos
class EventCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre de la Categoría")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    is_active = models.BooleanField(default=True, verbose_name="Activa")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    class Meta:
        ordering = ['name']
        verbose_name = "Categoría de Evento"
        verbose_name_plural = "Categorías de Eventos"

    def __str__(self):
        return self.name

# Modelo para eventos (actualizado)
class Event(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nombre del Evento")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    event_date = models.DateField(verbose_name="Fecha del Evento")
    location = models.CharField(max_length=200, verbose_name="Ubicación")
    organizer = models.CharField(max_length=200, verbose_name="Organizador")
    disciplines = models.ManyToManyField(Discipline, related_name='events', blank=True, verbose_name="Disciplinas")
    categories = models.ManyToManyField(EventCategory, related_name='events', blank=True, verbose_name="Categorías del Evento")
    is_verified = models.BooleanField(default=False, verbose_name="Verificado")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='created_events',
        verbose_name="Creado por"
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='verified_events',
        verbose_name="Verificado por"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación", null=True)
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de verificación")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"

    def __str__(self):
        return f"{self.name} - {self.event_date}"

# Modelo de participación en eventos (actualizado con sistema dinámico)
class EventParticipation(models.Model):
    RESULT_CHOICES = [
        ('1st', 'Primer Lugar'),
        ('2nd', 'Segundo Lugar'),
        ('3rd', 'Tercer Lugar'),
        ('4th', 'Cuarto Lugar'),
        ('5th', 'Quinto Lugar'),
        ('participation', 'Participación'),
        ('exhibition', 'Exhibición'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='participations', verbose_name="Evento")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_participations', verbose_name="Usuario")
    event_category = models.ForeignKey(EventCategory, on_delete=models.CASCADE, related_name='participations', verbose_name="Categoría del Evento")
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, verbose_name="Resultado")
    is_verified = models.BooleanField(default=False, verbose_name="Verificado")
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='verified_participations',
        verbose_name="Verificado por"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro", null=True)
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de verificación")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Participación en Evento"
        verbose_name_plural = "Participaciones en Eventos"
        unique_together = ('event', 'user', 'event_category')  # Un usuario no puede participar en la misma categoría del mismo evento dos veces

    def __str__(self):
        return f"{self.user.email} - {self.event.name} ({self.event_category.name}) - {self.get_result_display()}"
