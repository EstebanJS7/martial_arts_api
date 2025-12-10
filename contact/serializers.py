from rest_framework import serializers
from .models import ContactMessage, Academy


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'message']


class AcademySerializer(serializers.ModelSerializer):
    """Serializer para listar academias (público)"""
    coordinates = serializers.SerializerMethodField()

    class Meta:
        model = Academy
        fields = ['id', 'name', 'address', 'phone', 'email', 'schedule', 'latitude', 'longitude', 'coordinates', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_coordinates(self, obj):
        return obj.coordinates


class AcademyCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar academias (solo admin)"""

    class Meta:
        model = Academy
        fields = ['name', 'address', 'phone', 'email', 'schedule', 'latitude', 'longitude', 'is_active']


