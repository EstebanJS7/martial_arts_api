from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from .models import Class, UserClassReservation

User = get_user_model()

class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = '__all__'
        read_only_fields = ('reservation_count',)
    
    def create(self, validated_data):
        # Asegurar que las fechas tengan timezone si no la tienen
        if 'date' in validated_data and validated_data['date'] and timezone.is_naive(validated_data['date']):
            validated_data['date'] = timezone.make_aware(validated_data['date'])
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Asegurar que las fechas tengan timezone si no la tienen
        if 'date' in validated_data and validated_data['date'] and timezone.is_naive(validated_data['date']):
            validated_data['date'] = timezone.make_aware(validated_data['date'])
        return super().update(instance, validated_data)

class UserClassReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserClassReservation
        fields = '__all__'
        read_only_fields = ('user', 'created_at',)

class MultiClassCreateSerializer(serializers.Serializer):
    """
    Serializer para crear múltiples clases a la vez.
    Se espera recibir una lista de clases con los datos necesarios.
    """
    classes = ClassSerializer(many=True)

    def create(self, validated_data):
        classes_data = validated_data.pop('classes')
        classes_instances = []
        
        for item in classes_data:
            # Asegurar que las fechas tengan timezone si no la tienen
            if 'date' in item and item['date'] and timezone.is_naive(item['date']):
                item['date'] = timezone.make_aware(item['date'])
            classes_instances.append(Class(**item))
            
        return Class.objects.bulk_create(classes_instances)

class MultiClassUpdateSerializer(serializers.Serializer):
    """
    Serializer para actualizar múltiples clases.
    Se espera una lista de objetos que contenga al menos el id y los campos a modificar.
    """
    id = serializers.IntegerField()
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    date = serializers.DateTimeField(required=False)
    duration = serializers.DurationField(required=False)
    max_students = serializers.IntegerField(required=False)
    instructor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False
    )

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
