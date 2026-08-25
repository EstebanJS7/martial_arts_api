# models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
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

# Modelo para gestionar los cinturones
class BeltRank(models.Model):
    CATEGORY_CHOICES = [
        ('Kyu A', 'Kyu A'),
        ('Kyu B', 'Kyu B'),
        ('Dan', 'Dan'),
    ]
    
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre del Cinturón')
    order_number = models.IntegerField(unique=True, verbose_name='Número de Orden', 
                                       help_text='Número único que indica el orden del cinturón (1=Blanco, 2=Naranja, etc.)')
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, verbose_name='Categoría')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de Actualización')

    class Meta:
        ordering = ['order_number']
        verbose_name = 'Cinturón'
        verbose_name_plural = 'Cinturones'
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    def get_next_belt(self):
        """Retorna el siguiente cinturón en orden"""
        try:
            return BeltRank.objects.filter(
                order_number__gt=self.order_number,
                is_active=True
            ).order_by('order_number').first()
        except BeltRank.DoesNotExist:
            return None

    def get_previous_belt(self):
        """Retorna el cinturón anterior en orden"""
        try:
            return BeltRank.objects.filter(
                order_number__lt=self.order_number,
                is_active=True
            ).order_by('-order_number').first()
        except BeltRank.DoesNotExist:
            return None

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
    belt_rank = models.ForeignKey(
        'BeltRank',
        on_delete=models.PROTECT,
        related_name='exam_sessions',
        verbose_name='Cinturón a Evaluar',
        help_text='Cinturón que se evaluará en esta sesión de examen',
        null=True,
        blank=True,
    )
    belt_level = models.CharField(max_length=50, blank=True, null=True)  # Mantener para compatibilidad
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
        return f"Exam Session for {self.belt_rank.name} on {self.exam_date}"

    def save(self, *args, **kwargs):
        # Mantener compatibilidad con belt_level
        if self.belt_rank and not self.belt_level:
            self.belt_level = self.belt_rank.name
        super().save(*args, **kwargs)

class ExamResult(models.Model):
    """
    Representa el resultado de un participante en una sesión de examen.
    Cada participante tendrá un único resultado por sesión.
    """
    exam_session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='exam_results')
    participant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_results')
    graded = models.BooleanField(default=False)  # Indica si ya fue calificado
    passed = models.BooleanField(default=False, verbose_name='Aprobado', 
                                 help_text='Indica si el participante aprobó el examen')

    class Meta:
        unique_together = ('exam_session', 'participant')
        verbose_name = "Exam Result"
        verbose_name_plural = "Exam Results"

    def __str__(self):
        return f"Result for {self.participant.email} in {self.exam_session}"

    def save(self, *args, **kwargs):
        """Actualiza el cinturón del usuario si aprueba el examen"""
        is_new = self.pk is None
        old_passed = None
        if not is_new:
            try:
                old_instance = ExamResult.objects.get(pk=self.pk)
                old_passed = old_instance.passed
            except ExamResult.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Si el examen fue calificado y aprobado, y antes no estaba aprobado, actualizar el cinturón
        if self.graded and self.passed and (is_new or (old_passed is not None and not old_passed)):
            self.update_user_belt()

    def update_user_belt(self):
        """Actualiza el cinturón del usuario al cinturón del examen aprobado"""
        try:
            user_profile = self.participant.userprofile
            new_belt = self.exam_session.belt_rank
            
            # Actualizar el cinturón del usuario usando ForeignKey
            user_profile.belt_rank = new_belt
            user_profile.save()
            
            # Log para debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Usuario {self.participant.email} actualizado a cinturón {new_belt.name}")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error actualizando cinturón para {self.participant.email}: {e}")

    @staticmethod
    def can_take_exam(user, exam_session):
        """
        Valida si un usuario puede tomar un examen para un cinturón específico.
        Solo puede tomar examen para el siguiente cinturón después del suyo actual.
        """
        try:
            user_profile = user.userprofile
            current_belt_name = user_profile.belt_rank
            
            # Si no tiene cinturón asignado, solo puede tomar el primer cinturón
            if not current_belt_name or current_belt_name.strip() == '':
                first_belt = BeltRank.objects.filter(is_active=True).order_by('order_number').first()
                if first_belt and first_belt.id == exam_session.belt_rank.id:
                    return True
                return False
            
            # Buscar el cinturón actual del usuario
            try:
                current_belt = BeltRank.objects.get(name=current_belt_name, is_active=True)
            except BeltRank.DoesNotExist:
                # Si el cinturón actual no existe en el sistema, permitir el examen
                # (para compatibilidad con datos antiguos)
                return True
            
            # El siguiente cinturón debe ser el del examen
            next_belt = current_belt.get_next_belt()
            
            if next_belt and next_belt.id == exam_session.belt_rank.id:
                return True
            
            # Si el usuario ya tiene un cinturón igual o superior, no puede tomar el examen
            if current_belt.order_number >= exam_session.belt_rank.order_number:
                return False
            
            return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error validando si usuario puede tomar examen: {e}")
            return False

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
        Actualiza las estadísticas basadas en asistencias reales a clases,
        exámenes (ExamSession) y participaciones en eventos.
        """
        # Import local para evitar dependencias entre apps al cargar módulos.
        from classes.models import ClassAttendance

        # Asistencia real: registros ClassAttendance marcados como presentes por
        # el instructor, en clases pasadas y no canceladas. Antes se contaban
        # reservas activas (UserClassReservation), lo que inflaba la tasa cerca
        # del 100% aunque el alumno faltara a la clase.
        self.classes_attended = ClassAttendance.objects.filter(
            user=self.user,
            attended=True,
            class_reserved__is_cancelled=False,
            class_reserved__date__lt=timezone.now(),
        ).count()
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
