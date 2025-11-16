from rest_framework import serializers

from .models import Notification, UserNotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'title', 'message', 'type', 'data', 'is_read', 'created_at']
        read_only_fields = ['id', 'recipient', 'created_at']


class NotificationReadSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class UserNotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotificationPreference
        fields = ['enabled', 'receive_realtime']








