# Generated manually
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('classes', '0007_classtemplate_classattendance'),
        ('users', '0001_initial'),  # Asegurar que existe la dependencia de users
    ]

    operations = [
        migrations.AddField(
            model_name='class',
            name='class_type',
            field=models.CharField(
                choices=[
                    ('regular', 'Regular'),
                    ('intensive', 'Intensiva'),
                    ('private', 'Privada'),
                    ('seminar', 'Seminario'),
                    ('exam', 'Examen'),
                ],
                default='regular',
                help_text='Tipo de clase',
                max_length=50
            ),
        ),
        migrations.AddField(
            model_name='class',
            name='difficulty_level',
            field=models.CharField(
                choices=[
                    ('kyu_a', 'Kyu A'),
                    ('kyu_b', 'Kyu B'),
                    ('dan', 'Dan'),
                    ('all', 'Todos'),
                ],
                default='all',
                help_text='Nivel de dificultad',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='class',
            name='location',
            field=models.CharField(
                blank=True,
                help_text='Ubicación de la clase (sala, dojo, etc.)',
                max_length=200
            ),
        ),
        migrations.AddField(
            model_name='class',
            name='equipment_needed',
            field=models.TextField(
                blank=True,
                help_text='Equipamiento requerido para la clase'
            ),
        ),
        migrations.AddField(
            model_name='class',
            name='notes',
            field=models.TextField(
                blank=True,
                help_text='Notas adicionales sobre la clase'
            ),
        ),
        migrations.AddField(
            model_name='class',
            name='is_cancelled',
            field=models.BooleanField(
                default=False,
                help_text='Indica si la clase ha sido cancelada'
            ),
        ),
        migrations.AddField(
            model_name='class',
            name='cancellation_reason',
            field=models.TextField(
                blank=True,
                help_text='Razón de la cancelación'
            ),
        ),
        migrations.AddField(
            model_name='class',
            name='cancelled_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Usuario que canceló la clase',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='cancelled_classes',
                to='users.customuser'
            ),
        ),
        migrations.AddField(
            model_name='class',
            name='cancelled_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Fecha y hora de cancelación',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='class',
            name='attendance_count',
            field=models.IntegerField(
                default=0,
                help_text='Número de estudiantes que asistieron'
            ),
        ),
        migrations.AddField(
            model_name='class',
            name='no_show_count',
            field=models.IntegerField(
                default=0,
                help_text='Número de estudiantes que no asistieron (no shows)'
            ),
        ),
    ]




