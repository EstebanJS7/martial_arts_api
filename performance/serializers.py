# serializers.py
from rest_framework import serializers
from django.conf import settings
from .models import (
    EvaluationParameter,
    ExamSession,
    ExamResult,
    ExamResultParameterScore,
    PerformanceStatistics,
)
from django.contrib.auth import get_user_model

User = get_user_model()

# Para los parámetros de evaluación
class EvaluationParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationParameter
        fields = ['id', 'name', 'description']

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

    class Meta:
        model = ExamResult
        fields = ['id', 'exam_session', 'participant', 'graded', 'parameter_scores']
        read_only_fields = ['participant', 'graded']

    def create(self, validated_data):
        scores_data = validated_data.pop('parameter_scores')
        exam_result = ExamResult.objects.create(**validated_data)
        for score_data in scores_data:
            ExamResultParameterScore.objects.create(exam_result=exam_result, **score_data)
        return exam_result

    def update(self, instance, validated_data):
        scores_data = validated_data.pop('parameter_scores', None)
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

    class Meta:
        model = ExamSession
        fields = ['id', 'belt_level', 'exam_date', 'created_by', 'participants']
        read_only_fields = ['created_by']

    def create(self, validated_data):
        participants = validated_data.pop('participants', [])
        exam_session = ExamSession.objects.create(**validated_data)
        exam_session.participants.set(participants)
        # Opcional: Crear automáticamente un ExamResult para cada participante
        for user in participants:
            ExamResult.objects.get_or_create(exam_session=exam_session, participant=user)
        return exam_session
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
