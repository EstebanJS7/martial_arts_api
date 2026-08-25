from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_payment_period(apps, schema_editor):
    """Rellena el período (YYYY-MM) de los pagos existentes a partir de su fecha de vencimiento."""
    Payment = apps.get_model('payments', 'Payment')
    for payment in Payment.objects.all().iterator():
        if payment.due_date:
            payment.period = payment.due_date.strftime('%Y-%m')
            payment.save(update_fields=['period'])


def clear_payment_period(apps, schema_editor):
    """Reversa del backfill: deja el período en NULL."""
    Payment = apps.get_model('payments', 'Payment')
    Payment.objects.update(period=None)


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0009_payment_payments_pa_user_id_aa2b55_idx_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Período de la cuota (YYYY-MM): se agrega nullable, se rellena desde
        # due_date y luego pasa a ser obligatorio.
        migrations.AddField(
            model_name='payment',
            name='period',
            field=models.CharField(help_text='Período de la cuota (YYYY-MM)', max_length=7, null=True),
        ),
        migrations.RunPython(backfill_payment_period, clear_payment_period),
        migrations.AlterField(
            model_name='payment',
            name='period',
            field=models.CharField(help_text='Período de la cuota (YYYY-MM)', max_length=7),
        ),
        migrations.AddField(
            model_name='payment',
            name='is_overdue',
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['user', 'period'], name='payments_pa_user_id_6602a6_idx'),
        ),
        # Auditoría de transacciones: quién registró, método con choices explícitos,
        # referencia del comprobante y número de recibo secuencial.
        migrations.AddField(
            model_name='paymenttransaction',
            name='registered_by',
            field=models.ForeignKey(blank=True, help_text='Usuario que registró la transacción', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='registered_transactions', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='paymenttransaction',
            name='payment_method',
            field=models.CharField(blank=True, choices=[('cash', 'Efectivo'), ('transfer', 'Transferencia')], help_text='Método de pago (efectivo o transferencia)', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='paymenttransaction',
            name='reference_number',
            field=models.CharField(blank=True, help_text='Número de comprobante/voucher (para transferencias)', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='paymenttransaction',
            name='receipt_number',
            field=models.CharField(blank=True, help_text='Número secuencial de recibo por año (formato RC-YYYY-NNNNNN)', max_length=20, null=True, unique=True),
        ),
    ]
