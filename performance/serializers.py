from rest_framework import serializers
from .models import PerformanceStatistics, BeltExam, EventParticipation, EvaluationParameter, ExamParameterScore, Discipline

class EvaluationParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationParameter
        fields = ['id', 'name', 'description']

class ExamParameterScoreSerializer(serializers.ModelSerializer):
    # Para escritura, se acepta únicamente el ID del parámetro
    parameter = serializers.PrimaryKeyRelatedField(queryset=EvaluationParameter.objects.all())

    class Meta:
        model = ExamParameterScore
        fields = ['id', 'exam', 'parameter', 'score']
    
    def to_representation(self, instance):
        """ Representa el parámetro de forma anidada usando EvaluationParameterSerializer """
        rep = super().to_representation(instance)
        rep['parameter'] = EvaluationParameterSerializer(instance.parameter).data
        return rep

class BeltExamSerializer(serializers.ModelSerializer):
    # Se usa el serializer anterior para manejar la creación y actualización de las puntuaciones
    parameters_evaluated = ExamParameterScoreSerializer(many=True)

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
            parameter_obj = parameter_data.get('parameter')
            # Si se envía como diccionario, se extrae el id; si no, se asume que es una instancia
            if isinstance(parameter_obj, dict):
                parameter_id = parameter_obj.get('id')
            else:
                parameter_id = parameter_obj.id
            score = parameter_data.get('score')
            ExamParameterScore.objects.update_or_create(
                exam=instance,
                parameter_id=parameter_id,
                defaults={'score': score},
            )
        return instance

class EventParticipationSerializer(serializers.ModelSerializer):
    # Se permite la asignación de disciplinas mediante su nombre
    disciplines = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=Discipline.objects.all()
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
