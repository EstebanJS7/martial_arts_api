# Generated manually for events system migration

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


def clear_old_event_participations(apps, schema_editor):
    """
    Elimina todos los registros antiguos de EventParticipation
    """
    EventParticipation = apps.get_model('performance', 'EventParticipation')
    EventParticipation.objects.all().delete()


def create_sample_events(apps, schema_editor):
    """
    Crea algunos eventos de ejemplo para el nuevo sistema
    """
    Event = apps.get_model('performance', 'Event')
    User = apps.get_model('users', 'CustomUser')
    UserProfile = apps.get_model('users', 'UserProfile')
    
    # Buscar un usuario admin o instructor para crear eventos
    admin_profiles = UserProfile.objects.filter(role__in=['admin', 'instructor'])
    admin_user = admin_profiles.first().user if admin_profiles.exists() else None
    
    if not admin_user:
        # Si no hay admin, usar el primer usuario disponible
        admin_user = User.objects.first()
    
    if admin_user:
        # Crear algunos eventos de ejemplo
        sample_events = [
            {
                'name': 'Campeonato Nacional de Karate 2024',
                'description': 'Campeonato nacional de karate con categorías desde principiantes hasta avanzados',
                'event_date': '2024-12-15',
                'location': 'Centro de Convenciones, Ciudad de México',
                'organizer': 'Federación Nacional de Karate',
                'is_verified': True,
                'created_by': admin_user,
                'verified_by': admin_user,
            },
            {
                'name': 'Torneo Regional de Taekwondo',
                'description': 'Torneo regional de taekwondo para todas las edades',
                'event_date': '2024-11-20',
                'location': 'Gimnasio Municipal, Guadalajara',
                'organizer': 'Asociación Regional de Taekwondo',
                'is_verified': True,
                'created_by': admin_user,
                'verified_by': admin_user,
            },
            {
                'name': 'Exhibición de Artes Marciales',
                'description': 'Exhibición de diferentes estilos de artes marciales',
                'event_date': '2024-10-10',
                'location': 'Plaza Principal, Monterrey',
                'organizer': 'Centro de Artes Marciales Monterrey',
                'is_verified': False,
                'created_by': admin_user,
            }
        ]
        
        for event_data in sample_events:
            Event.objects.create(**event_data)


class Migration(migrations.Migration):

    dependencies = [
        ('performance', '0004_evaluationparameter_category'),
        ('users', '0001_initial'),
    ]

    operations = [
        # 1. Eliminar registros antiguos de EventParticipation
        migrations.RunPython(clear_old_event_participations),
        
        # 2. Crear el nuevo modelo Event
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Nombre del Evento')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Descripción')),
                ('event_date', models.DateField(verbose_name='Fecha del Evento')),
                ('location', models.CharField(max_length=200, verbose_name='Ubicación')),
                ('organizer', models.CharField(max_length=200, verbose_name='Organizador')),
                ('is_verified', models.BooleanField(default=False, verbose_name='Verificado')),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Fecha de creación')),
                ('verified_at', models.DateTimeField(blank=True, null=True, verbose_name='Fecha de verificación')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_events', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('disciplines', models.ManyToManyField(blank=True, related_name='events', to='performance.discipline', verbose_name='Disciplinas')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_events', to=settings.AUTH_USER_MODEL, verbose_name='Verificado por')),
            ],
            options={
                'verbose_name': 'Evento',
                'verbose_name_plural': 'Eventos',
                'ordering': ['-created_at'],
            },
        ),
        
        # 3. Actualizar EventParticipation para usar el nuevo sistema
        migrations.RemoveField(
            model_name='eventparticipation',
            name='disciplines',
        ),
        migrations.RemoveField(
            model_name='eventparticipation',
            name='event_date',
        ),
        migrations.RemoveField(
            model_name='eventparticipation',
            name='event_name',
        ),
        migrations.AddField(
            model_name='eventparticipation',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='Fecha de registro'),
        ),
        migrations.AddField(
            model_name='eventparticipation',
            name='event',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='participations', to='performance.event', verbose_name='Evento'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='eventparticipation',
            name='is_verified',
            field=models.BooleanField(default=False, verbose_name='Verificado'),
        ),
        migrations.AddField(
            model_name='eventparticipation',
            name='verified_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Fecha de verificación'),
        ),
        migrations.AddField(
            model_name='eventparticipation',
            name='verified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_participations', to=settings.AUTH_USER_MODEL, verbose_name='Verificado por'),
        ),
        migrations.AlterField(
            model_name='eventparticipation',
            name='category',
            field=models.CharField(choices=[('First Place', 'Primer Lugar'), ('Second Place', 'Segundo Lugar'), ('Third Place', 'Tercer Lugar'), ('Exhibition', 'Exhibición')], max_length=20, verbose_name='Categoría'),
        ),
        migrations.AlterModelOptions(
            name='eventparticipation',
            options={'ordering': ['-created_at'], 'verbose_name': 'Participación en Evento', 'verbose_name_plural': 'Participaciones en Eventos'},
        ),
        migrations.AddConstraint(
            model_name='eventparticipation',
            constraint=models.UniqueConstraint(fields=('event', 'user', 'category'), name='unique_event_user_category'),
        ),
        
        # 4. Crear eventos de ejemplo
        migrations.RunPython(create_sample_events),
    ]
