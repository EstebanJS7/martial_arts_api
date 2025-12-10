"""
ASGI config for martial_arts_api project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import json
import logging
import sys

# IMPORTANTE: Configurar Django settings ANTES de cualquier importación de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'martial_arts_api.settings')

# Obtener DEBUG de settings después de configurar el módulo
from django.conf import settings as django_settings
DEBUG = getattr(django_settings, 'DEBUG', False)

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

from .routing import websocket_urlpatterns
from notifications.middleware import JWTAuthMiddlewareStack

# Configurar logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[ASGI-HealthCheck] %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

django_asgi_app = get_asgi_application()


class HealthCheckASGIMiddleware:
    """
    Middleware ASGI que intercepta peticiones a /health/ antes de que Django las procese.
    Esto funciona a nivel de ASGI, antes de que los middlewares de Django se ejecuten.
    """
    
    def __init__(self, app):
        self.app = app
        logger.info("HealthCheckASGIMiddleware inicializado")
    
    async def __call__(self, scope, receive, send):
        try:
            # Solo procesar peticiones HTTP
            if scope.get('type') == 'http':
                path = scope.get('path', '')
                method = scope.get('method', '')
                
                # Interceptar /health o /health/ (sin logs excesivos)
                if path == '/health' or path == '/health/':
                    logger.info(f"[ASGI] Interceptando /health -> 200 OK")
                    
                    # Crear respuesta HTTP 200 directamente
                    response_body = json.dumps({
                        "status": "healthy",
                        "service": "martial_arts_api"
                    }).encode('utf-8')
                    
                    await send({
                        'type': 'http.response.start',
                        'status': 200,
                        'headers': [
                            [b'content-type', b'application/json'],
                            [b'content-length', str(len(response_body)).encode()],
                        ],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': response_body,
                    })
                    return
            
            # Para todas las demás peticiones, continuar con el flujo normal
            await self.app(scope, receive, send)
        except Exception as e:
            logger.error(f"[ASGI] ERROR en HealthCheckASGIMiddleware: {e}", exc_info=True)
            # Si hay un error, intentar continuar con el flujo normal
            try:
                await self.app(scope, receive, send)
            except Exception as e2:
                logger.error(f"[ASGI] ERROR crítico: {e2}", exc_info=True)
                # Devolver error 500
                error_body = json.dumps({
                    "error": "Internal Server Error",
                    "detail": str(e2) if DEBUG else "An error occurred"
                }).encode('utf-8')
                await send({
                    'type': 'http.response.start',
                    'status': 500,
                    'headers': [
                        [b'content-type', b'application/json'],
                        [b'content-length', str(len(error_body)).encode()],
                    ],
                })
                await send({
                    'type': 'http.response.body',
                    'body': error_body,
                })


# Aplicar el middleware ASGI antes de Django
application = ProtocolTypeRouter({
    'http': HealthCheckASGIMiddleware(django_asgi_app),
    'websocket': JWTAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
