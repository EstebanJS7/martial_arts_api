from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Class(models.Model):
    name = models.CharField(max_length=100)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='instructed_classes')
    date = models.DateTimeField()
    max_students = models.IntegerField()

    def __str__(self):
        return self.name

class UserClassReservation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    class_reserved = models.ForeignKey(Class, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} reserved {self.class_reserved.name}"