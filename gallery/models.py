from django.db import models

class Gallery(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Galería"
        verbose_name_plural = "Galerías"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class GalleryItem(models.Model):
    MEDIA_TYPE_CHOICES = (
        ('image', 'Image'),
        ('video', 'Video'),
    )
    # Considera eliminar el default y hacerlo obligatorio:
    gallery = models.ForeignKey('Gallery', on_delete=models.CASCADE, null=False, blank=False)
    media_type = models.CharField(max_length=5, choices=MEDIA_TYPE_CHOICES, default='image')
    image = models.ImageField(upload_to='gallery/images/', blank=True, null=True)
    video = models.FileField(upload_to='gallery/videos/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Elemento de Galería"
        verbose_name_plural = "Elementos de Galería"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.media_type}: {self.description or 'Unnamed'}"
