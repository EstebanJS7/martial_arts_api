from django.contrib import admin

from .models import Notification, UserNotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'title', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__email')


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'enabled', 'receive_realtime')
    list_filter = ('enabled', 'receive_realtime')
    search_fields = ('user__email',)









