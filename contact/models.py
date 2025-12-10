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


class Academy(models.Model):
    """Modelo para representar las academias/sucursales del sistema"""
    name = models.CharField(max_length=255, verbose_name='Nombre de la Academia')
    address = models.CharField(max_length=500, verbose_name='Dirección')
    phone = models.CharField(max_length=20, verbose_name='Teléfono')
    email = models.EmailField(verbose_name='Correo Electrónico')
    schedule = models.CharField(max_length=200, verbose_name='Horario', help_text='Ej: Lun-Vie: 8:00 AM - 9:00 PM')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, verbose_name='Latitud')
    longitude = models.DecimalField(max_digits=9, decimal_places=6, verbose_name='Longitud')
    is_active = models.BooleanField(default=True, verbose_name='Activa')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de Actualización')

    class Meta:
        ordering = ['name']
        verbose_name = 'Academia'
        verbose_name_plural = 'Academias'

    def __str__(self):
        return self.name

    @property
    def coordinates(self):
        """Retorna las coordenadas como tupla para uso en mapas"""
        return [float(self.latitude), float(self.longitude)]


