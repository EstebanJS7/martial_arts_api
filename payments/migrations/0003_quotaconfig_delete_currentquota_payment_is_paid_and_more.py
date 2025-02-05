# Generated by Django 5.1 on 2024-09-13 19:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuotaConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('due_day', models.IntegerField(default=10)),
            ],
        ),
        migrations.DeleteModel(
            name='CurrentQuota',
        ),
        migrations.AddField(
            model_name='payment',
            name='is_paid',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='payment',
            name='due_date',
            field=models.DateField(),
        ),
    ]
