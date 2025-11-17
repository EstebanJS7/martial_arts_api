"""
Management command para enviar recordatorios de clases.
Este comando debe ejecutarse periódicamente (cada 15-30 minutos) usando cron o un scheduler.
"""
from django.core.management.base import BaseCommand
from notifications.notification_scheduler import NotificationScheduler


class Command(BaseCommand):
    help = 'Envía recordatorios de clases (24h y 1h antes) y recordatorios de asistencia'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reminder-type',
            type=str,
            choices=['24h', '1h', 'attendance', 'all'],
            default='all',
            help='Tipo de recordatorio a enviar (24h, 1h, attendance, o all)',
        )

    def handle(self, *args, **options):
        reminder_type = options['reminder_type']
        
        if reminder_type == 'all' or reminder_type == '24h':
            count_24h = NotificationScheduler.send_class_reminders_24h()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Enviados {count_24h} recordatorios de 24 horas')
            )
        
        if reminder_type == 'all' or reminder_type == '1h':
            count_1h = NotificationScheduler.send_class_reminders_1h()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Enviados {count_1h} recordatorios de 1 hora')
            )
        
        if reminder_type == 'all' or reminder_type == 'attendance':
            count_attendance = NotificationScheduler.send_attendance_reminders()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Enviados {count_attendance} recordatorios de asistencia')
            )
        
        if reminder_type == 'all':
            self.stdout.write(
                self.style.SUCCESS('✓ Todos los recordatorios han sido procesados')
            )


