from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import BeltExam, EventParticipation, PerformanceStatistics

@receiver(post_save, sender=BeltExam)
def update_stats_after_belt_exam(sender, instance, created, **kwargs):
    """
    Actualiza las estadísticas cuando se crea o actualiza un BeltExam.
    """
    stats, _ = PerformanceStatistics.objects.get_or_create(user=instance.user)
    stats.update_statistics()

@receiver(post_delete, sender=BeltExam)
def update_stats_after_belt_exam_delete(sender, instance, **kwargs):
    """
    Actualiza las estadísticas cuando se elimina un BeltExam.
    """
    stats, _ = PerformanceStatistics.objects.get_or_create(user=instance.user)
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
