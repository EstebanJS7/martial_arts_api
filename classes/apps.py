from django.apps import AppConfig


class ClassesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'classes'
    verbose_name = 'Clases'
    def ready(self):
        from . import signals  # noqa: F401
