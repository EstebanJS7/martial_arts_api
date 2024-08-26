from django.db import models
from django.contrib.auth.models import User

class Discipline(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class EvaluationParameter(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class BeltExam(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='belt_exams')
    belt_level = models.CharField(max_length=50)  # Ejemplo: "Black Belt"
    exam_date = models.DateField()
    parameters_evaluated = models.ManyToManyField(EvaluationParameter, through='ExamParameterScore', related_name='belt_exams')  # Relación ManyToMany a través de un modelo intermedio
    passed = models.BooleanField(default=False)

    class Meta:
        ordering = ['exam_date']
        verbose_name = "Belt Exam"
        verbose_name_plural = "Belt Exams"

    def __str__(self):
        return f"{self.user.username} - {self.belt_level} exam on {self.exam_date}"

class ExamParameterScore(models.Model):
    exam = models.ForeignKey(BeltExam, on_delete=models.CASCADE)
    parameter = models.ForeignKey(EvaluationParameter, on_delete=models.CASCADE)
    score = models.IntegerField()

    def __str__(self):
        return f"{self.exam} - {self.parameter.name} Score: {self.score}"

class EventParticipation(models.Model):
    EVENT_CATEGORIES = [
        ('First Place', 'First Place'),
        ('Second Place', 'Second Place'),
        ('Third Place', 'Third Place'),
        ('Exhibition', 'Exhibition'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_participations')
    event_name = models.CharField(max_length=200)
    disciplines = models.ManyToManyField(Discipline, related_name='event_participations')
    category = models.CharField(max_length=20, choices=EVENT_CATEGORIES)
    event_date = models.DateField()

    class Meta:
        ordering = ['event_date']
        verbose_name = "Event Participation"
        verbose_name_plural = "Event Participations"

    def __str__(self):
        return f"{self.user.username} - {self.event_name} ({self.category})"

class PerformanceStatistics(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    classes_attended = models.IntegerField(default=0)
    belt_exams = models.ManyToManyField(BeltExam, related_name='performance_statistics', blank=True)
    event_participations = models.ManyToManyField(EventParticipation, related_name='performance_statistics', blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Performance Statistic"
        verbose_name_plural = "Performance Statistics"

    def __str__(self):
        return f"Performance stats for {self.user.username}"

    def update_statistics(self):
        """ Utility method to update statistics based on exams and events """
        self.classes_attended = self.user.userclassreservation_set.count()
        self.belt_exams.set(self.user.belt_exams.all())
        self.event_participations.set(self.user.event_participations.all())
        self.save()
