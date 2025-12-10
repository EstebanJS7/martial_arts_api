from django.contrib import admin
from .models import ContactMessage, Academy


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'created_at', 'is_read']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'email', 'message']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(Academy)
class AcademyAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'phone', 'email', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'address', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'is_active')
        }),
        ('Contacto', {
            'fields': ('address', 'phone', 'email', 'schedule')
        }),
        ('Ubicación', {
            'fields': ('latitude', 'longitude')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at')
        }),
    )


