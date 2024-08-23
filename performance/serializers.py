from rest_framework import serializers
from .models import PerformanceStatistics, BeltExam, EventParticipation, Discipline

class DisciplineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discipline
        fields = '__all__'

class BeltExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = BeltExam
        fields = '__all__'
        
    def validate(self, data):
        # Solo los instructores pueden crear o modificar exámenes de cinturón
        if self.context['request'].user.userprofile.role != 'instructor':
            raise serializers.ValidationError("Only instructors can modify belt exams.")
        return data

class EventParticipationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventParticipation
        fields = '__all__'

class PerformanceStatisticsSerializer(serializers.ModelSerializer):
    belt_exams = BeltExamSerializer(many=True)
    event_participations = EventParticipationSerializer(many=True)

    class Meta:
        model = PerformanceStatistics
        fields = '__all__'