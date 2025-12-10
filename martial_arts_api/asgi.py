"""
ASGI config for martial_arts_api project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

# IMPORTANTE: Configurar Django settings ANTES de cualquier importación de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'martial_arts_api.settings')

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

from .routing import websocket_urlpatterns
from notifications.middleware import JWTAuthMiddlewareStack

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': JWTAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
