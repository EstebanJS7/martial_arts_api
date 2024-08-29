from django.db import models
from django.conf import settings

# Create your models here.
class Class(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='instructed_classes')
    date = models.DateTimeField()
    max_students = models.IntegerField()

    def __str__(self):
        return self.name
class UserClassReservation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    class_reserved = models.ForeignKey(Class, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('user', 'class_reserved')

    def __str__(self):
        return f'{self.user.email} - {self.class_reserved.name}'