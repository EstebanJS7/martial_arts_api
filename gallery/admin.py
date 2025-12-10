from django.contrib import admin
from .models import Gallery, GalleryItem

@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title',)

@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ('gallery', 'media_type', 'uploaded_at')
    list_filter = ('media_type', 'gallery')
    search_fields = ('description',)
