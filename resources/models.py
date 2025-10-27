from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class ResourceType(models.TextChoices):
    VIDEO = 'VIDEO', _('Video')
    DOCUMENT = 'DOCUMENT', _('Documento')
    LINK = 'LINK', _('Enlace')
    IMAGE = 'IMAGE', _('Imagen')
    AUDIO = 'AUDIO', _('Audio')

class ResourceCategory(models.TextChoices):
    TECHNIQUE = 'TECHNIQUE', _('Técnica')
    THEORY = 'THEORY', _('Teoría')
    HISTORY = 'HISTORY', _('Historia')
    PHILOSOPHY = 'PHILOSOPHY', _('Filosofía')
    TRAINING = 'TRAINING', _('Entrenamiento')
    COMPETITION = 'COMPETITION', _('Competición')
    OTHER = 'OTHER', _('Otro')

class ResourceLevel(models.TextChoices):
    KYU_A = 'KYU_A', _('Kyu A')
    KYU_B = 'KYU_B', _('Kyu B')
    DAN = 'DAN', _('Dan')
    ALL = 'ALL', _('Todos los niveles')

class ResourceTag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        verbose_name = "Etiqueta de recurso"
        verbose_name_plural = "Etiquetas de recursos"
    
    def __str__(self):
        return self.name

class Resource(models.Model):
    title = models.CharField(max_length=200, verbose_name=_("Título"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Descripción"))
    type = models.CharField(
        max_length=20,
        choices=ResourceType.choices,
        default=ResourceType.DOCUMENT,
        verbose_name=_("Tipo")
    )
    category = models.CharField(
        max_length=20,
        choices=ResourceCategory.choices,
        default=ResourceCategory.OTHER,
        verbose_name=_("Categoría")
    )
    level = models.CharField(
        max_length=20,
        choices=ResourceLevel.choices,
        default=ResourceLevel.ALL,
        verbose_name=_("Nivel")
    )
    url = models.URLField(blank=True, null=True, verbose_name=_("URL"))
    file = models.FileField(upload_to='resources/', blank=True, null=True, verbose_name=_("Archivo"))
    thumbnail = models.ImageField(upload_to='resources/thumbnails/', blank=True, null=True, verbose_name=_("Miniatura"))
    file_size = models.PositiveIntegerField(blank=True, null=True, verbose_name=_("Tamaño del archivo"))
    duration = models.PositiveIntegerField(blank=True, null=True, verbose_name=_("Duración (segundos)"))
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Fecha de creación"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Fecha de actualización"))
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='resources',
        verbose_name=_("Autor"),
        null=True,
        blank=True
    )
    tags = models.ManyToManyField(ResourceTag, blank=True, related_name='resources', verbose_name=_("Etiquetas"))
    views_count = models.PositiveIntegerField(default=0, verbose_name=_("Número de vistas"))
    downloads_count = models.PositiveIntegerField(default=0, verbose_name=_("Número de descargas"))
    is_featured = models.BooleanField(default=False, verbose_name=_("Destacado"))
    is_premium = models.BooleanField(default=False, verbose_name=_("Premium"))

    class Meta:
        verbose_name = _("Recurso")
        verbose_name_plural = _("Recursos")
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
    def increment_views(self):
        self.views_count += 1
        self.save(update_fields=['views_count'])
        
    def increment_downloads(self):
        self.downloads_count += 1
        self.save(update_fields=['downloads_count'])
