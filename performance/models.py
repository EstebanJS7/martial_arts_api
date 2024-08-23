from django.db import models
from django.contrib.auth.models import User

class Discipline(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class BeltExam(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='belt_exams')
    belt_level = models.CharField(max_length=50)  # Ejemplo: "Black Belt"
    exam_date = models.DateField()
    parameters_evaluated = models.JSONField()  # Almacena los parámetros y puntuaciones como JSON
    passed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.belt_level} exam on {self.exam_date}"

class EventParticipation(models.Model):
    EVENT_CATEGORIES = [
        ('First Place', 'First Place'),
        ('Second Place', 'Second Place'),
        ('Third Place', 'Third Place'),
        ('Exhibition', 'Exhibition'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_participations')
    event_name = models.CharField(max_length=200)
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=EVENT_CATEGORIES)
    event_date = models.DateField()

    def __str__(self):
        return f"{self.user.username} - {self.event_name} ({self.category})"

class PerformanceStatistics(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    classes_attended = models.IntegerField(default=0)
    belt_exams = models.ManyToManyField(BeltExam, related_name='performance_statistics')
    event_participations = models.ManyToManyField(EventParticipation, related_name='performance_statistics')
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Performance stats for {self.user.username}"