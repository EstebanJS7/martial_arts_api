from rest_framework import serializers
from .models import PerformanceStatistics, BeltExam, EventParticipation, EvaluationParameter, ExamParameterScore

class EvaluationParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationParameter
        fields = ['id', 'name', 'description']

class ExamParameterScoreSerializer(serializers.ModelSerializer):
    parameter = EvaluationParameterSerializer()

    class Meta:
        model = ExamParameterScore
        fields = ['id', 'exam', 'parameter', 'score']

class BeltExamSerializer(serializers.ModelSerializer):
    parameters_evaluated = ExamParameterScoreSerializer(many=True)  # Ahora permite crear y actualizar puntuaciones de parámetros

    class Meta:
        model = BeltExam
        fields = ['id', 'user', 'belt_level', 'exam_date', 'parameters_evaluated', 'passed']

    def create(self, validated_data):
        parameters_data = validated_data.pop('parameters_evaluated')
        belt_exam = BeltExam.objects.create(**validated_data)
        for parameter_data in parameters_data:
            ExamParameterScore.objects.create(exam=belt_exam, **parameter_data)
        return belt_exam

    def update(self, instance, validated_data):
        parameters_data = validated_data.pop('parameters_evaluated')
        instance.belt_level = validated_data.get('belt_level', instance.belt_level)
        instance.exam_date = validated_data.get('exam_date', instance.exam_date)
        instance.passed = validated_data.get('passed', instance.passed)
        instance.save()

        # Actualizar o crear las puntuaciones de parámetros
        for parameter_data in parameters_data:
            parameter_id = parameter_data.get('parameter').id
            score = parameter_data.get('score')

            exam_parameter_score, created = ExamParameterScore.objects.update_or_create(
                exam=instance,
                parameter_id=parameter_id,
                defaults={'score': score},
            )
        return instance

class EventParticipationSerializer(serializers.ModelSerializer):
    disciplines = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name'
    )

    class Meta:
        model = EventParticipation
        fields = ['id', 'user', 'event_name', 'disciplines', 'category', 'event_date']

class PerformanceStatisticsSerializer(serializers.ModelSerializer):
    belt_exams = BeltExamSerializer(many=True, read_only=True)
    event_participations = EventParticipationSerializer(many=True, read_only=True)

    class Meta:
        model = PerformanceStatistics
        fields = ['user', 'classes_attended', 'belt_exams', 'event_participations', 'last_updated']
