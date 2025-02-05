# Generated by Django 5.1 on 2024-09-13 21:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0003_quotaconfig_delete_currentquota_payment_is_paid_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='amount_paid',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='payment',
            name='is_fully_paid',
            field=models.BooleanField(default=False),
        ),
    ]
