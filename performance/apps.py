from django.apps import AppConfig

class PerformanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'performance'
    verbose_name = 'Desempeño'

    def ready(self):
        import performance.signals  # Esto carga las señales
