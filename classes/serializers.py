from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from .models import Class, UserClassReservation, ClassAttendance, ClassTemplate, ClassWaitlist

User = get_user_model()

class ClassSerializer(serializers.ModelSerializer):
    instructor_name = serializers.SerializerMethodField()
    instructor_full_name = serializers.SerializerMethodField()
    instructor_email = serializers.SerializerMethodField()
    available_spots = serializers.SerializerMethodField()
    is_reserved = serializers.SerializerMethodField()
    is_reservable = serializers.SerializerMethodField()
    is_in_waitlist = serializers.SerializerMethodField()
    waitlist_count = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    formatted_duration = serializers.SerializerMethodField()
    class_type_display = serializers.CharField(source='get_class_type_display', read_only=True)
    difficulty_level_display = serializers.CharField(source='get_difficulty_level_display', read_only=True)
    cancelled_by_email = serializers.SerializerMethodField()
    cancelled_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Class
        fields = '__all__'
        read_only_fields = (
            'reservation_count', 
            'attendance_count', 
            'no_show_count',
            'cancelled_at',
        )
    
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
        1. No está cancelada
        2. Es futura (date > now)
        3. Tiene cupos disponibles
        4. El usuario no tiene ya una reserva
        """
        # Verificar que no esté cancelada
        if obj.is_cancelled:
            return False
        
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
    
    def get_is_in_waitlist(self, obj):
        """Verifica si el usuario actual está en la lista de espera de esta clase."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.waitlist_entries.filter(
                user=request.user,
                status='waiting'
            ).exists()
        return False
    
    def get_waitlist_count(self, obj):
        """Retorna el número de usuarios en la lista de espera."""
        return obj.waitlist_entries.filter(status='waiting').count()
    
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
    
    def get_cancelled_by_email(self, obj):
        return obj.cancelled_by.email if obj.cancelled_by else None
    
    def get_cancelled_by_name(self, obj):
        if obj.cancelled_by:
            first_name = obj.cancelled_by.first_name or ""
            last_name = obj.cancelled_by.last_name or ""
            if first_name or last_name:
                return f"{first_name} {last_name}".strip()
            return obj.cancelled_by.email
        return None
    
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
    class_type = serializers.CharField(required=False)
    difficulty_level = serializers.CharField(required=False)
    location = serializers.CharField(required=False, allow_blank=True)
    equipment_needed = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    is_cancelled = serializers.BooleanField(required=False)
    cancellation_reason = serializers.CharField(required=False, allow_blank=True)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ClassAttendanceSerializer(serializers.ModelSerializer):
    """Serializer para el registro de asistencia de clases."""
    user_email = serializers.SerializerMethodField()
    user_full_name = serializers.SerializerMethodField()
    class_name = serializers.SerializerMethodField()
    marked_by_email = serializers.SerializerMethodField()
    
    class Meta:
        model = ClassAttendance
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'marked_by')
    
    def get_user_email(self, obj):
        return obj.user.email if obj.user else None
    
    def get_user_full_name(self, obj):
        if obj.user:
            first_name = obj.user.first_name or ""
            last_name = obj.user.last_name or ""
            if first_name or last_name:
                return f"{first_name} {last_name}".strip()
            return obj.user.email
        return None
    
    def get_class_name(self, obj):
        return obj.class_reserved.name if obj.class_reserved else None
    
    def get_marked_by_email(self, obj):
        return obj.marked_by.email if obj.marked_by else None


class ClassAttendanceCreateSerializer(serializers.Serializer):
    """Serializer para crear/actualizar asistencia."""
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    attended = serializers.BooleanField()
    notes = serializers.CharField(required=False, allow_blank=True)
    check_in_time = serializers.DateTimeField(required=False, allow_null=True)
    check_out_time = serializers.DateTimeField(required=False, allow_null=True)


class ClassTemplateSerializer(serializers.ModelSerializer):
    """Serializer para plantillas de clases."""
    instructor_name = serializers.SerializerMethodField()
    instructor_email = serializers.SerializerMethodField()
    class_type_display = serializers.CharField(source='get_class_type_display', read_only=True)
    difficulty_level_display = serializers.CharField(source='get_difficulty_level_display', read_only=True)
    
    class Meta:
        model = ClassTemplate
        fields = '__all__'
    
    def get_instructor_name(self, obj):
        if obj.instructor:
            first_name = obj.instructor.first_name or ""
            last_name = obj.instructor.last_name or ""
            if first_name or last_name:
                return f"{first_name} {last_name}".strip()
            return obj.instructor.email
        return None
    
    def get_instructor_email(self, obj):
        return obj.instructor.email if obj.instructor else None


class ClassTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear clases desde plantillas."""
    template_id = serializers.IntegerField(required=False)
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    frequency = serializers.ChoiceField(
        choices=[
            ('daily', 'Diario'),
            ('weekly', 'Semanal'),
            ('monthly', 'Mensual'),
        ],
        default='weekly'
    )
    days_of_week = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        required=False,
        help_text="Días de la semana (0=Lunes, 6=Domingo)"
    )


class ClassWaitlistSerializer(serializers.ModelSerializer):
    """Serializer para la lista de espera de clases."""
    user_email = serializers.SerializerMethodField()
    user_full_name = serializers.SerializerMethodField()
    class_name = serializers.SerializerMethodField()
    class_date = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ClassWaitlist
        fields = '__all__'
        read_only_fields = ('user', 'position', 'joined_at', 'created_at', 'updated_at')
    
    def get_user_email(self, obj):
        return obj.user.email if obj.user else None
    
    def get_user_full_name(self, obj):
        if obj.user:
            first_name = obj.user.first_name or ""
            last_name = obj.user.last_name or ""
            if first_name or last_name:
                return f"{first_name} {last_name}".strip()
            return obj.user.email
        return None
    
    def get_class_name(self, obj):
        return obj.class_reserved.name if obj.class_reserved else None
    
    def get_class_date(self, obj):
        if obj.class_reserved and obj.class_reserved.date:
            return obj.class_reserved.date.strftime("%d/%m/%Y %H:%M")
        return None


class ClassWaitlistCreateSerializer(serializers.Serializer):
    """Serializer para crear una entrada en la lista de espera."""
    class_id = serializers.IntegerField()
