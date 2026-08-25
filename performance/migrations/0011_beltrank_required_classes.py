# Migración manual (estilo Django 5.1) - 2026-08-24
# Agrega el requisito configurable de clases por cinturón.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('performance', '0010_examresult_passed_alter_examsession_belt_level_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='beltrank',
            name='required_classes',
            field=models.IntegerField(blank=True, default=20, help_text='Clases mínimas asistidas en el rango actual requeridas para habilitar el examen del siguiente cinturón (por defecto 20)', null=True, verbose_name='Clases Requeridas'),
        ),
    ]
