from django.db import models
from django.utils import timezone


class ContactMessage(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Mensaje de Contacto'
        verbose_name_plural = 'Mensajes de Contacto'

    def __str__(self):
        return f'Mensaje de {self.name} - {self.email}'

