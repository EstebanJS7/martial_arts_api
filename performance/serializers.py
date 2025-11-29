# serializers.py
from rest_framework import serializers
from django.conf import settings
from .models import (
    EvaluationParameter,
    BeltRank,
    ExamSession,
    ExamResult,
    ExamResultParameterScore,
    PerformanceStatistics,
    EventCategory,
    Event,
    EventParticipation,
)
from django.contrib.auth import get_user_model

User = get_user_model()

# Para los parámetros de evaluación
class EvaluationParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationParameter
        fields = ['id', 'name', 'description', 'category']

# Serializador para cinturones
class BeltRankSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = BeltRank
        fields = ['id', 'name', 'order_number', 'category', 'category_display', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class BeltRankCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BeltRank
        fields = ['name', 'order_number', 'category', 'is_active']

# Serializador para las puntuaciones en un resultado de examen
class ExamResultParameterScoreSerializer(serializers.ModelSerializer):
    parameter = serializers.PrimaryKeyRelatedField(queryset=EvaluationParameter.objects.all())

    class Meta:
        model = ExamResultParameterScore
        fields = ['id', 'parameter', 'score']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['parameter'] = EvaluationParameterSerializer(instance.parameter).data
        return rep

# Serializador para el resultado del examen de un participante
class ExamResultSerializer(serializers.ModelSerializer):
    parameter_scores = ExamResultParameterScoreSerializer(many=True)
    participant_name = serializers.SerializerMethodField()
    belt_level = serializers.CharField(source='exam_session.belt_level', read_only=True)
    belt_rank_name = serializers.CharField(source='exam_session.belt_rank.name', read_only=True)

    def get_participant_name(self, obj):
        """Devuelve el nombre completo del participante o el email si no tiene nombre"""
        if obj.participant.first_name and obj.participant.last_name:
            return f"{obj.participant.first_name} {obj.participant.last_name}"
        elif obj.participant.first_name:
            return obj.participant.first_name
        elif obj.participant.last_name:
            return obj.participant.last_name
        else:
            return obj.participant.email

    class Meta:
        model = ExamResult
        fields = ['id', 'exam_session', 'participant', 'participant_name', 'belt_level', 'belt_rank_name', 'graded', 'passed', 'parameter_scores']
        read_only_fields = ['graded', 'passed']  # graded y passed se calculan automáticamente

    def create(self, validated_data):
        scores_data = validated_data.pop('parameter_scores', [])
        # Establecer graded=True cuando se crea con calificaciones
        validated_data['graded'] = True
        # Calcular si pasó basado en las puntuaciones (puedes ajustar la lógica)
        validated_data['passed'] = self._calculate_passed(scores_data)
        exam_result = ExamResult.objects.create(**validated_data)
        for score_data in scores_data:
            ExamResultParameterScore.objects.create(exam_result=exam_result, **score_data)
        return exam_result

    def update(self, instance, validated_data):
        scores_data = validated_data.pop('parameter_scores', None)
        # Guardar el estado anterior de passed para detectar cambios
        old_passed = instance.passed
        old_graded = instance.graded
        
        # Marcar como calificado si se están actualizando las puntuaciones
        if scores_data is not None:
            validated_data['graded'] = True
            # Recalcular si pasó
            validated_data['passed'] = self._calculate_passed(scores_data)
        
        # Actualizamos otros campos si es necesario
        instance = super().update(instance, validated_data)
        
        if scores_data is not None:
            # Eliminar puntuaciones existentes y crear nuevas
            instance.parameter_scores.all().delete()
            for score_data in scores_data:
                ExamResultParameterScore.objects.create(exam_result=instance, **score_data)
        
        # Si cambió de no aprobado a aprobado, actualizar el cinturón
        if (not old_passed and instance.passed) or (not old_graded and instance.graded and instance.passed):
            instance.update_user_belt()
        
        return instance

    def _calculate_passed(self, scores_data):
        """Calcula si el examen fue aprobado basado en las puntuaciones"""
        if not scores_data:
            return False
        # Lógica simple: aprobar si todas las puntuaciones son >= 7 (puedes ajustar)
        # O puedes usar una lógica más compleja
        min_score = 7  # Puntuación mínima para aprobar
        return all(score.get('score', 0) >= min_score for score in scores_data)

# Serializador para la sesión de examen
class ExamSessionSerializer(serializers.ModelSerializer):
    participants = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all())
    evaluation_parameters = serializers.PrimaryKeyRelatedField(many=True, queryset=EvaluationParameter.objects.all(), required=False)
    belt_rank_name = serializers.CharField(source='belt_rank.name', read_only=True)
    belt_rank_order = serializers.IntegerField(source='belt_rank.order_number', read_only=True)

    class Meta:
        model = ExamSession
        fields = ['id', 'belt_rank', 'belt_rank_name', 'belt_rank_order', 'belt_level', 'exam_date', 'created_by', 'participants', 'evaluation_parameters']
        read_only_fields = ['created_by', 'belt_level']

    def create(self, validated_data):
        participants = validated_data.pop('participants', [])
        evaluation_parameters = validated_data.pop('evaluation_parameters', [])
        
        # Validar participantes ANTES de crear la sesión
        invalid_participants = []
        belt_rank = validated_data.get('belt_rank')
        belt_rank_name = 'N/A'
        
        # Obtener el nombre del cinturón de forma segura
        if belt_rank:
            belt_rank_name = belt_rank.name
        
        # Crear una sesión temporal para validar (sin guardar en BD)
        # Necesitamos crear un objeto ExamSession temporal con los datos validados
        temp_exam_session = ExamSession(
            belt_rank=belt_rank,
            exam_date=validated_data.get('exam_date'),
            created_by=validated_data.get('created_by')
        )
        
        # Validar cada participante
        for user in participants:
            if not ExamResult.can_take_exam(user, temp_exam_session):
                # Obtener información del usuario para el mensaje de error
                user_name = user.email
                if user.first_name or user.last_name:
                    user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
                invalid_participants.append({
                    'id': user.id,
                    'email': user.email,
                    'name': user_name
                })
        
        # Si hay participantes inválidos, lanzar error
        if invalid_participants:
            invalid_names = [p['name'] for p in invalid_participants]
            raise serializers.ValidationError({
                'participants': [
                    f"Los siguientes usuarios no pueden tomar este examen para el cinturón '{belt_rank_name}': {', '.join(invalid_names)}. "
                    f"Un usuario solo puede tomar examen para el siguiente cinturón después del suyo actual."
                ],
                'invalid_participants': invalid_participants
            })
        
        # Si todos los participantes son válidos, crear la sesión y los resultados
        exam_session = ExamSession.objects.create(**validated_data)
        exam_session.participants.set(participants)
        exam_session.evaluation_parameters.set(evaluation_parameters)
        
        # Crear automáticamente un ExamResult para cada participante válido
        for user in participants:
            ExamResult.objects.get_or_create(exam_session=exam_session, participant=user)
        
        return exam_session

# Serializador para EventCategory
class EventCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCategory
        fields = ['id', 'name', 'description', 'is_active', 'created_at']
        read_only_fields = ['created_at']

# Serializador para Event (actualizado)
class EventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.email', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.email', read_only=True)
    categories_data = EventCategorySerializer(source='categories', many=True, read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'id', 'name', 'description', 'event_date', 'location', 'organizer',
            'disciplines', 'categories', 'categories_data', 'is_verified', 
            'created_by', 'created_by_name', 'verified_by', 'verified_by_name', 
            'created_at', 'verified_at'
        ]
        read_only_fields = ['created_by', 'verified_by', 'created_at', 'verified_at']

# Serializador para EventParticipation (actualizado con sistema dinámico)
class EventParticipationSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    event_date = serializers.DateField(source='event.event_date', read_only=True)
    event_location = serializers.CharField(source='event.location', read_only=True)
    user_name = serializers.SerializerMethodField()
    verified_by_name = serializers.CharField(source='verified_by.email', read_only=True)
    event_category_name = serializers.CharField(source='event_category.name', read_only=True)
    result_display = serializers.CharField(source='get_result_display', read_only=True)
    
    def get_user_name(self, obj):
        """Devuelve el nombre completo del usuario o el email si no tiene nombre"""
        if obj.user.first_name and obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name}"
        elif obj.user.first_name:
            return obj.user.first_name
        elif obj.user.last_name:
            return obj.user.last_name
        else:
            return obj.user.email
    
    class Meta:
        model = EventParticipation
        fields = [
            'id', 'event', 'event_name', 'event_date', 'event_location',
            'user', 'user_name', 'event_category', 'event_category_name', 
            'result', 'result_display', 'is_verified',
            'verified_by', 'verified_by_name', 'created_at', 'verified_at'
        ]
        read_only_fields = ['user', 'verified_by', 'created_at', 'verified_at']

# Serializador para PerformanceStatistics
class PerformanceStatisticsSerializer(serializers.ModelSerializer):
    # Se anidan los resultados de examen y las participaciones en eventos
    belt_exams = serializers.SerializerMethodField()
    event_participations = serializers.SerializerMethodField()

    class Meta:
        model = PerformanceStatistics
        fields = ['user', 'classes_attended', 'belt_exams', 'event_participations', 'last_updated']

    def get_belt_exams(self, obj):
        # Para simplificar, se listan los IDs de las sesiones a las que el usuario participó
        return [session.id for session in obj.user.exam_sessions.all()]

    def get_event_participations(self, obj):
        return [ep.id for ep in obj.user.event_participations.all()]
