from django.contrib import admin
from .models import Resource, ResourceTag

@admin.register(ResourceTag)
class ResourceTagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'category', 'level', 'author', 'created_at', 'is_featured', 'is_premium', 'views_count')
    list_filter = ('type', 'category', 'level', 'is_featured', 'is_premium', 'created_at')
    search_fields = ('title', 'description', 'author__username', 'author__email')
    readonly_fields = ('created_at', 'updated_at', 'views_count', 'downloads_count')
    filter_horizontal = ('tags',)
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Información básica', {
            'fields': ('title', 'description', 'author', 'type', 'category', 'level')
        }),
        ('Contenido', {
            'fields': ('url', 'file', 'thumbnail', 'file_size', 'duration')
        }),
        ('Clasificación', {
            'fields': ('tags',)
        }),
        ('Estadísticas', {
            'fields': ('views_count', 'downloads_count', 'created_at', 'updated_at')
        }),
        ('Opciones', {
            'fields': ('is_featured', 'is_premium')
        }),
    )