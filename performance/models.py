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

# Modelo de participación en eventos (ya existente)
class EventParticipation(models.Model):
    EVENT_CATEGORIES = [
        ('First Place', 'First Place'),
        ('Second Place', 'Second Place'),
        ('Third Place', 'Third Place'),
        ('Exhibition', 'Exhibition'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_participations')
    event_name = models.CharField(max_length=200)
    disciplines = models.ManyToManyField(Discipline, related_name='event_participations')
    category = models.CharField(max_length=20, choices=EVENT_CATEGORIES)
    event_date = models.DateField()

    class Meta:
        ordering = ['event_date']
        verbose_name = "Event Participation"
        verbose_name_plural = "Event Participations"

    def __str__(self):
        return f"{self.user.email} - {self.event_name} ({self.category})"
