from rest_framework import serializers
from .models import Class, UserClassReservation

class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = '__all__'
        read_only_fields = ('instructor',)  # El instructor se asigna automáticamente

    def create(self, validated_data):
        user = self.context['request'].user
        # Validar que el usuario tenga un perfil y que su rol sea 'instructor' o 'admin'
        if not hasattr(user, 'userprofile') or user.userprofile.role not in ['instructor', 'admin']:
            raise serializers.ValidationError("Solo los instructores y administradores pueden crear clases.")
        # Asignar el usuario autenticado como instructor si no se envía en la petición
        validated_data.setdefault('instructor', user)
        return super().create(validated_data)

class UserClassReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserClassReservation
        fields = '__all__'
        read_only_fields = ('user', 'created_at')
