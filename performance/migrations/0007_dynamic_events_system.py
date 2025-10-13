# Generated manually for dynamic events system migration

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


def clear_old_event_participations(apps, schema_editor):
    """
    Elimina todos los registros antiguos de EventParticipation
    """
    EventParticipation = apps.get_model('performance', 'EventParticipation')
    EventParticipation.objects.all().delete()


def create_default_event_categories(apps, schema_editor):
    """
    Crea categorías de eventos por defecto
    """
    EventCategory = apps.get_model('performance', 'EventCategory')
    
    default_categories = [
        {
            'name': 'Combate',
            'description': 'Competencias de combate libre y por categorías de peso',
            'is_active': True,
        },
        {
            'name': 'Formas (Kata)',
            'description': 'Competencias de formas tradicionales y modernas',
            'is_active': True,
        },
        {
            'name': 'Exhibición',
            'description': 'Presentaciones y demostraciones artísticas',
            'is_active': True,
        },
        {
            'name': 'Formas por Equipos',
            'description': 'Competencias de formas en equipo',
            'is_active': True,
        },
        {
            'name': 'Defensa Personal',
            'description': 'Competencias de técnicas de defensa personal',
            'is_active': True,
        },
        {
            'name': 'Arma',
            'description': 'Competencias con armas tradicionales',
            'is_active': True,
        },
        {
            'name': 'Breaking',
            'description': 'Competencias de rompimiento de tablas',
            'is_active': True,
        },
        {
            'name': 'Sparring',
            'description': 'Competencias de combate controlado',
            'is_active': True,
        }
    ]
    
    for category_data in default_categories:
        EventCategory.objects.get_or_create(
            name=category_data['name'],
            defaults=category_data
        )


def update_existing_events(apps, schema_editor):
    """
    Actualiza eventos existentes para incluir categorías por defecto
    """
    Event = apps.get_model('performance', 'Event')
    EventCategory = apps.get_model('performance', 'EventCategory')
    
    # Obtener todas las categorías activas
    categories = EventCategory.objects.filter(is_active=True)
    
    # Asignar todas las categorías a eventos existentes
    for event in Event.objects.all():
        event.categories.set(categories)


class Migration(migrations.Migration):

    dependencies = [
        ('performance', '0006_remove_eventparticipation_unique_event_user_category_and_more'),
        ('users', '0001_initial'),
    ]

    operations = [
        # 1. Eliminar participaciones antiguas
        migrations.RunPython(clear_old_event_participations),
        
        # 2. Crear el modelo EventCategory
        migrations.CreateModel(
            name='EventCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nombre de la Categoría')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Descripción')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activa')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
            ],
            options={
                'verbose_name': 'Categoría de Evento',
                'verbose_name_plural': 'Categorías de Eventos',
                'ordering': ['name'],
            },
        ),
        
        # 3. Agregar campo categories a Event
        migrations.AddField(
            model_name='event',
            name='categories',
            field=models.ManyToManyField(blank=True, related_name='events', to='performance.eventcategory', verbose_name='Categorías del Evento'),
        ),
        
        # 4. Agregar campos a EventParticipation
        migrations.AddField(
            model_name='eventparticipation',
            name='event_category',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='participations', to='performance.eventcategory', verbose_name='Categoría del Evento'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='eventparticipation',
            name='result',
            field=models.CharField(choices=[('1st', 'Primer Lugar'), ('2nd', 'Segundo Lugar'), ('3rd', 'Tercer Lugar'), ('4th', 'Cuarto Lugar'), ('5th', 'Quinto Lugar'), ('participation', 'Participación'), ('exhibition', 'Exhibición')], default='participation', max_length=20, verbose_name='Resultado'),
            preserve_default=False,
        ),
        
        # 5. Crear categorías por defecto
        migrations.RunPython(create_default_event_categories),
        
        # 6. Actualizar eventos existentes
        migrations.RunPython(update_existing_events),
        
        # 7. Actualizar unique_together después de crear las categorías
        migrations.AlterUniqueTogether(
            name='eventparticipation',
            unique_together={('event', 'user', 'event_category')},
        ),
    ]


