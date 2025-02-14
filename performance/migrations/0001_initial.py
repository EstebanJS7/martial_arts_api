# Generated by Django 5.1 on 2024-08-23 00:31

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Discipline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='BeltExam',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('belt_level', models.CharField(max_length=50)),
                ('exam_date', models.DateField()),
                ('parameters_evaluated', models.JSONField()),
                ('passed', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='belt_exams', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='EventParticipation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_name', models.CharField(max_length=200)),
                ('category', models.CharField(choices=[('First Place', 'First Place'), ('Second Place', 'Second Place'), ('Third Place', 'Third Place'), ('Exhibition', 'Exhibition')], max_length=20)),
                ('event_date', models.DateField()),
                ('discipline', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='performance.discipline')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='event_participations', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PerformanceStatistics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('classes_attended', models.IntegerField(default=0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('belt_exams', models.ManyToManyField(related_name='performance_statistics', to='performance.beltexam')),
                ('event_participations', models.ManyToManyField(related_name='performance_statistics', to='performance.eventparticipation')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
