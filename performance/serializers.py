# serializers.py
from rest_framework import serializers
from django.conf import settings
from .models import (
    EvaluationParameter,
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
        fields = ['id', 'exam_session', 'participant', 'participant_name', 'belt_level', 'graded', 'parameter_scores']
        read_only_fields = ['graded']  # Solo graded es read-only, participant debe ser escribible

    def create(self, validated_data):
        scores_data = validated_data.pop('parameter_scores')
        # Establecer graded=True cuando se crea con calificaciones
        validated_data['graded'] = True
        exam_result = ExamResult.objects.create(**validated_data)
        for score_data in scores_data:
            ExamResultParameterScore.objects.create(exam_result=exam_result, **score_data)
        return exam_result

    def update(self, instance, validated_data):
        scores_data = validated_data.pop('parameter_scores', None)
        # Marcar como calificado si se están actualizando las puntuaciones
        if scores_data is not None:
            validated_data['graded'] = True
        # Actualizamos otros campos si es necesario
        instance = super().update(instance, validated_data)
        if scores_data is not None:
            for score_data in scores_data:
                parameter = score_data.get('parameter')
                score = score_data.get('score')
                ExamResultParameterScore.objects.update_or_create(
                    exam_result=instance,
                    parameter=parameter,
                    defaults={'score': score},
                )
        return instance

# Serializador para la sesión de examen
class ExamSessionSerializer(serializers.ModelSerializer):
    participants = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all())
    evaluation_parameters = serializers.PrimaryKeyRelatedField(many=True, queryset=EvaluationParameter.objects.all(), required=False)

    class Meta:
        model = ExamSession
        fields = ['id', 'belt_level', 'exam_date', 'created_by', 'participants', 'evaluation_parameters']
        read_only_fields = ['created_by']

    def create(self, validated_data):
        participants = validated_data.pop('participants', [])
        evaluation_parameters = validated_data.pop('evaluation_parameters', [])
        exam_session = ExamSession.objects.create(**validated_data)
        exam_session.participants.set(participants)
        exam_session.evaluation_parameters.set(evaluation_parameters)
        # Opcional: Crear automáticamente un ExamResult para cada participante
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
