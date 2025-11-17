"""
Utilidades para generar y validar códigos QR para check-in de clases.
"""
import qrcode
import io
from django.http import HttpResponse
from django.utils import timezone
from .models import Class, UserClassReservation, ClassAttendance


def generate_qr_code_image(qr_data: str) -> bytes:
    """
    Genera una imagen de código QR a partir de los datos proporcionados.
    
    Args:
        qr_data: Datos a codificar en el QR
        
    Returns:
        bytes: Imagen del QR en formato PNG
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir a bytes
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer.getvalue()


def validate_qr_token_and_checkin(token: str, user) -> dict:
    """
    Valida un token QR y realiza el check-in del usuario si es válido.
    
    Args:
        token: Token del código QR
        user: Usuario que está haciendo check-in
        
    Returns:
        dict: Resultado de la operación con información de la clase y estado
    """
    try:
        # Buscar la clase por token
        class_obj = Class.objects.get(qr_code_token=token)
    except Class.DoesNotExist:
        return {
            'success': False,
            'error': 'Código QR inválido o clase no encontrada',
        }
    
    # Verificar que la clase no esté cancelada
    if class_obj.is_cancelled:
        return {
            'success': False,
            'error': 'Esta clase ha sido cancelada',
        }
    
    # Verificar que la clase sea futura o reciente (dentro de 1 hora después)
    now = timezone.now()
    class_end_time = class_obj.date + class_obj.duration
    
    # Permitir check-in hasta 1 hora después de que termine la clase
    if now > class_end_time + timezone.timedelta(hours=1):
        return {
            'success': False,
            'error': 'El tiempo para hacer check-in ha expirado',
        }
    
    # Verificar que el usuario tenga reserva para esta clase
    reservation = UserClassReservation.objects.filter(
        class_reserved=class_obj,
        user=user,
        is_cancelled=False
    ).first()
    
    if not reservation:
        return {
            'success': False,
            'error': 'No tienes una reserva para esta clase',
        }
    
    # Verificar si ya tiene asistencia marcada
    attendance, created = ClassAttendance.objects.get_or_create(
        class_reserved=class_obj,
        user=user,
        defaults={
            'attended': True,
            'check_in_time': now,
            'marked_by': user,
        }
    )
    
    if not created and attendance.attended:
        return {
            'success': False,
            'error': 'Ya has hecho check-in para esta clase',
            'class_name': class_obj.name,
            'check_in_time': attendance.check_in_time.isoformat() if attendance.check_in_time else None,
        }
    
    # Actualizar asistencia si ya existía pero no estaba marcada
    if not created:
        attendance.attended = True
        attendance.check_in_time = now
        attendance.marked_by = user
        attendance.save()
    
    return {
        'success': True,
        'message': 'Check-in realizado exitosamente',
        'class_name': class_obj.name,
        'class_date': class_obj.date.isoformat(),
        'check_in_time': attendance.check_in_time.isoformat() if attendance.check_in_time else None,
    }


