from django.contrib import admin
from .models import PerformanceStatistics, BeltExam, EventParticipation, Discipline

admin.site.register(PerformanceStatistics)
admin.site.register(BeltExam)
admin.site.register(EventParticipation)
admin.site.register(Discipline)
