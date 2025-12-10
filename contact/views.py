from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.core.mail import send_mail
from django.conf import settings
from .serializers import ContactMessageSerializer
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def contact_form_view(request):
    """
    Endpoint para recibir mensajes del formulario de contacto.
    Envía un correo electrónico al administrador y guarda el mensaje en la base de datos.
    """
    serializer = ContactMessageSerializer(data=request.data)
    
    if serializer.is_valid():
        # Guardar el mensaje en la base de datos
        contact_message = serializer.save()
        
        # Preparar el contenido del correo
        subject = f'Nuevo mensaje de contacto de {contact_message.name}'
        message_body = f"""
Has recibido un nuevo mensaje de contacto:

Nombre: {contact_message.name}
Email: {contact_message.email}
Teléfono: {contact_message.phone or "No proporcionado"}

Mensaje:
{contact_message.message}

---
Este mensaje fue enviado desde el formulario de contacto de la página web.
        """
        
        # Obtener lista de administradores
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_emails = list(User.objects.filter(
            is_staff=True,
            is_active=True
        ).values_list('email', flat=True))
        
        # Si no hay administradores, usar el email por defecto
        if not admin_emails:
            admin_emails = [settings.EMAIL_HOST_USER] if settings.EMAIL_HOST_USER else []
        
        # Enviar correo al administrador
        try:
            if admin_emails:
                send_mail(
                    subject=subject,
                    message=message_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=False,
                )
            
            # También enviar confirmación al usuario
            confirmation_subject = 'Gracias por contactarnos - Martial Arts Academy'
            confirmation_message = f"""
Hola {contact_message.name},

Gracias por contactarnos. Hemos recibido tu mensaje y te responderemos pronto.

Tu mensaje:
{contact_message.message}

Saludos,
Equipo de Martial Arts Academy
            """
            
            send_mail(
                subject=confirmation_subject,
                message=confirmation_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[contact_message.email],
                fail_silently=False,
            )
            
            return Response(
                {
                    'success': True,
                    'message': 'Mensaje enviado correctamente. Te responderemos pronto.'
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f'Error enviando correo de contacto: {e}')
            # Aún así guardamos el mensaje en la BD
            return Response(
                {
                    'success': True,
                    'message': 'Mensaje recibido. Te contactaremos pronto.'
                },
                status=status.HTTP_201_CREATED
            )
    
    return Response(
        {
            'success': False,
            'errors': serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )

