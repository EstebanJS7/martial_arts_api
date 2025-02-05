from django.db import models
from django.conf import settings

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

    class Meta:
        unique_together = ('user', 'class_reserved')
        verbose_name = "Reserva de clase"
        verbose_name_plural = "Reservas de clases"

    def __str__(self):
        return f'{self.user.email} - {self.class_reserved.name}'
