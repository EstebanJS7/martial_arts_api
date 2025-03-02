from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ExamResult, EventParticipation, PerformanceStatistics

@receiver(post_save, sender=ExamResult)
def update_stats_after_exam_result(sender, instance, created, **kwargs):
    """
    Actualiza las estadísticas cuando se crea o actualiza un ExamResult.
    """
    stats, _ = PerformanceStatistics.objects.get_or_create(user=instance.participant)
    stats.update_statistics()

@receiver(post_delete, sender=ExamResult)
def update_stats_after_exam_result_delete(sender, instance, **kwargs):
    """
    Actualiza las estadísticas cuando se elimina un ExamResult.
    """
    stats, _ = PerformanceStatistics.objects.get_or_create(user=instance.participant)
    stats.update_statistics()

@receiver(post_save, sender=EventParticipation)
def update_stats_after_event_participation(sender, instance, created, **kwargs):
    """
    Actualiza las estadísticas cuando se crea o actualiza una EventParticipation.
    """
    stats, _ = PerformanceStatistics.objects.get_or_create(user=instance.user)
    stats.update_statistics()

@receiver(post_delete, sender=EventParticipation)
def update_stats_after_event_participation_delete(sender, instance, **kwargs):
    """
    Actualiza las estadísticas cuando se elimina una EventParticipation.
    """
    stats, _ = PerformanceStatistics.objects.get_or_create(user=instance.user)
    stats.update_statistics()
