from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from .models import Class, UserClassReservation

User = get_user_model()

class ClassSerializer(serializers.ModelSerializer):
    instructor_name = serializers.SerializerMethodField()
    instructor_full_name = serializers.SerializerMethodField()
    instructor_email = serializers.SerializerMethodField()
    available_spots = serializers.SerializerMethodField()
    is_reserved = serializers.SerializerMethodField()
    is_reservable = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    formatted_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Class
        fields = '__all__'
        read_only_fields = ('reservation_count',)
    
    def get_instructor_name(self, obj):
        if obj.instructor:
            return f"{obj.instructor.first_name or ''} {obj.instructor.last_name or ''}".strip() or obj.instructor.email
        return "Sin instructor asignado"
    
    def get_instructor_full_name(self, obj):
        if obj.instructor:
            first_name = obj.instructor.first_name or ""
            last_name = obj.instructor.last_name or ""
            if first_name or last_name:
                return f"{first_name} {last_name}".strip()
            return obj.instructor.email
        return "Sin instructor asignado"
    
    def get_instructor_email(self, obj):
        return obj.instructor.email if obj.instructor else None
    
    def get_available_spots(self, obj):
        return max(0, obj.max_students - obj.reservation_count)
    
    def get_is_reserved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.userclassreservation_set.filter(user=request.user).exists()
        return False
    
    def get_is_reservable(self, obj):
        """
        Una clase es reservable si:
        1. Es futura (date > now)
        2. Tiene cupos disponibles
        3. El usuario no tiene ya una reserva
        """
        now = timezone.now()
        
        # Verificar que sea futura
        if obj.date <= now:
            return False
        
        # Verificar que tenga cupos disponibles
        if obj.reservation_count >= obj.max_students:
            return False
        
        # Verificar que el usuario no tenga ya una reserva
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if obj.userclassreservation_set.filter(user=request.user).exists():
                return False
        
        return True
    
    def get_formatted_date(self, obj):
        if obj.date:
            return obj.date.strftime("%d/%m/%Y %H:%M")
        return None
    
    def get_formatted_duration(self, obj):
        if obj.duration:
            total_seconds = int(obj.duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            
            if hours > 0 and minutes > 0:
                return f"{hours}h {minutes}min"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}min"
        return "1h"  # Default
    
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
