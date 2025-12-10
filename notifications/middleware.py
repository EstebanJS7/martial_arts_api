"""
Middleware personalizado para autenticación JWT en WebSocket
"""
from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
import jwt

# No importar nada de Django o rest_framework_simplejwt a nivel de módulo
# para evitar problemas de importación. Se importarán de forma lazy dentro de las funciones


@database_sync_to_async
def get_user_from_token(token):
    """Obtiene el usuario desde un token JWT"""
    # Importaciones lazy para evitar problemas de inicialización de Django
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import AnonymousUser
    from django.conf import settings
    from rest_framework_simplejwt.tokens import UntypedToken
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
    
    User = get_user_model()  # Obtener el modelo de usuario de forma lazy
    
    try:
        # Validar el token
        UntypedToken(token)
    except (InvalidToken, TokenError) as e:
        return AnonymousUser()
    
    try:
        # Decodificar el token para obtener el user_id
        decoded_data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_data.get('user_id')
        
        if user_id:
            try:
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                return AnonymousUser()
    except Exception:
        return AnonymousUser()
    
    return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Middleware para autenticar usuarios en WebSocket usando JWT
    El token puede venir en:
    1. Query string: ?token=xxx
    2. Headers: Authorization: Bearer xxx
    """
    
    async def __call__(self, scope, receive, send):
        # Importación lazy de AnonymousUser
        from django.contrib.auth.models import AnonymousUser
        
        # Solo procesar conexiones WebSocket
        if scope["type"] != "websocket":
            return await super().__call__(scope, receive, send)
        
        # Obtener token de query string
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token = None
        
        # Intentar obtener token de query string
        if "token" in query_params:
            token = query_params["token"][0]
        
        # Si no hay token en query string, intentar obtenerlo de headers
        if not token:
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        # Autenticar usuario
        if token:
            scope["user"] = await get_user_from_token(token)
        else:
            scope["user"] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Stack de middleware para WebSocket con autenticación JWT"""
    return JWTAuthMiddleware(inner)

