#!/usr/bin/env python
"""
Script para crear notificaciones de prueba.
Uso: python manage.py shell < create_test_notifications.py
O ejecutar desde el shell de Django: exec(open('create_test_notifications.py').read())
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'martial_arts_api.settings')
django.setup()

from django.contrib.auth import get_user_model
from notifications.services import create_and_notify

User = get_user_model()

# Obtener el usuario admin
try:
    admin_user = User.objects.get(email='useradmin@gmail.com')
    print(f"✅ Usuario encontrado: {admin_user.email} (ID: {admin_user.id})")
except User.DoesNotExist:
    print("❌ Usuario no encontrado. Creando notificaciones públicas...")
    admin_user = None

# Crear varias notificaciones de prueba
notifications = [
    {
        'title': 'Bienvenido al Sistema',
        'message': '¡Bienvenido! Tu cuenta ha sido activada correctamente.',
        'type': 'success',
        'payload': {'action': 'welcome', 'user_id': admin_user.id if admin_user else None}
    },
    {
        'title': 'Nuevo Pago Recibido',
        'message': 'Se ha registrado un nuevo pago de $50.000. Estado: Completado.',
        'type': 'payment',
        'payload': {'payment_id': 1, 'amount': 50000, 'status': 'completed'}
    },
    {
        'title': 'Clase Próxima',
        'message': 'Tienes una clase de Taekwondo mañana a las 18:00. No olvides traer tu dobok.',
        'type': 'class',
        'payload': {'class_id': 1, 'class_name': 'Taekwondo Principiantes', 'date': '2024-11-16T18:00:00'}
    },
    {
        'title': 'Recordatorio de Pago',
        'message': 'Tu cuota mensual vence en 3 días. Por favor, realiza el pago a tiempo.',
        'type': 'warning',
        'payload': {'payment_id': 2, 'due_date': '2024-11-18', 'amount': 100000}
    },
    {
        'title': 'Asistencia Registrada',
        'message': 'Tu asistencia a la clase de Taekwondo del 15/11/2024 ha sido registrada.',
        'type': 'info',
        'payload': {'class_id': 1, 'attendance_id': 1, 'attended': True}
    },
    {
        'title': 'Error en el Sistema',
        'message': 'Hubo un problema al procesar tu última solicitud. Por favor, intenta nuevamente.',
        'type': 'error',
        'payload': {'error_code': 'ERR_001', 'action': 'retry'}
    },
]

print("\n📬 Creando notificaciones de prueba...\n")

created_count = 0
for notif_data in notifications:
    try:
        notification = create_and_notify(
            recipient_id=admin_user.id if admin_user else None,
            title=notif_data['title'],
            message=notif_data['message'],
            ntype=notif_data['type'],
            payload=notif_data.get('payload')
        )
        print(f"✅ Notificación creada: {notification.title} (ID: {notification.id}, Tipo: {notification.type})")
        created_count += 1
    except Exception as e:
        print(f"❌ Error al crear notificación '{notif_data['title']}': {e}")

print(f"\n🎉 Total de notificaciones creadas: {created_count}/{len(notifications)}")
print("\n💡 Las notificaciones deberían aparecer en tiempo real si el WebSocket está conectado.")
print("💡 También puedes verlas en: http://localhost:8000/admin/notifications/notification/")


