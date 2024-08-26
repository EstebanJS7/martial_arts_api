from django.db import models

class Resource(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='resources/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.title