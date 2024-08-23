from rest_framework import serializers
from .models import Class, UserClassReservation

class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = '__all__'
        
    def create(self, validated_data):
        user = self.context['request'].user
        if user.userprofile.role != 'instructor':
            raise serializers.ValidationError("Only instructors can create classes.")
        return super().create(validated_data)

class UserClassReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserClassReservation
        fields = '__all__'