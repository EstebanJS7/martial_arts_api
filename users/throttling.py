"""
Throttling personalizado para protección contra ataques y rate limiting.

Este módulo proporciona clases de throttling personalizadas para:
- Login (protección contra fuerza bruta)
- Registro de usuarios
- Reset de contraseña
- Endpoints sensibles
"""
from rest_framework.throttling import SimpleRateThrottle
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class LoginRateThrottle(SimpleRateThrottle):
    """
    Throttle para endpoints de login.
    Limita intentos de login por IP para prevenir ataques de fuerza bruta.
    """
    scope = 'login'

    def get_cache_key(self, request, view):
        """
        Genera una clave de caché basada en la IP del usuario.
        Solo aplica a usuarios no autenticados.
        """
        if request.user.is_authenticated:
            return None
        ident = self.get_ident(request)
        return f'throttle_login_{ident}'

    def throttle_success(self):
        """
        Método llamado cuando el throttle permite la solicitud.
        """
        logger.debug(f"Login request allowed for IP: {self.get_ident(self.request)}")
        return super().throttle_success()


class RegisterRateThrottle(SimpleRateThrottle):
    """
    Throttle para endpoints de registro de usuarios.
    Limita intentos de registro por IP para prevenir spam y abuso.
    """
    scope = 'register'

    def get_cache_key(self, request, view):
        """
        Genera una clave de caché basada en la IP del usuario.
        """
        ident = self.get_ident(request)
        return f'throttle_register_{ident}'


class PasswordResetRateThrottle(SimpleRateThrottle):
    """
    Throttle para endpoints de reset de contraseña.
    Limita intentos de reset por email para prevenir abuso.
    """
    scope = 'password_reset'

    def get_cache_key(self, request, view):
        """
        Genera una clave de caché basada en el email proporcionado.
        """
        email = request.data.get('email', '')
        if email:
            return f'throttle_password_reset_{email.lower()}'
        # Si no hay email, usar IP como fallback
        ident = self.get_ident(request)
        return f'throttle_password_reset_{ident}'


class PasswordResetConfirmRateThrottle(SimpleRateThrottle):
    """
    Throttle para confirmación de reset de contraseña.
    Limita intentos de confirmación por token.
    """
    scope = 'password_reset_confirm'

    def get_cache_key(self, request, view):
        """
        Genera una clave de caché basada en el token o UID proporcionado.
        """
        uid = request.data.get('uid', '')
        token = request.data.get('token', '')
        if uid and token:
            return f'throttle_password_reset_confirm_{uid}_{token[:10]}'
        # Si no hay uid/token, usar IP como fallback
        ident = self.get_ident(request)
        return f'throttle_password_reset_confirm_{ident}'


class SensitiveEndpointThrottle(SimpleRateThrottle):
    """
    Throttle para endpoints sensibles (pagos, cambios de perfil, etc.).
    Limita requests por usuario autenticado.
    """
    scope = 'sensitive'

    def get_cache_key(self, request, view):
        """
        Genera una clave de caché basada en el usuario autenticado o IP.
        """
        if request.user.is_authenticated:
            return f'throttle_sensitive_user_{request.user.id}'
        ident = self.get_ident(request)
        return f'throttle_sensitive_anon_{ident}'


class BruteForceProtectionThrottle(SimpleRateThrottle):
    """
    Throttle avanzado para protección contra fuerza bruta.
    Implementa bloqueo temporal después de múltiples intentos fallidos.
    """
    scope = 'brute_force'
    # Límites configurables
    MAX_FAILED_ATTEMPTS = 5  # Máximo de intentos fallidos
    LOCKOUT_DURATION = 900  # 15 minutos en segundos

    def get_cache_key(self, request, view):
        """
        Genera una clave de caché basada en el email o IP.
        """
        email = request.data.get('email', '')
        if email:
            return f'brute_force_{email.lower()}'
        ident = self.get_ident(request)
        return f'brute_force_{ident}'

    def allow_request(self, request, view):
        """
        Verifica si la solicitud está permitida.
        Bloquea temporalmente después de múltiples intentos fallidos.
        """
        cache_key = self.get_cache_key(request, view)
        
        # Verificar si está bloqueado
        lockout_key = f'{cache_key}_lockout'
        is_locked = cache.get(lockout_key)
        
        if is_locked:
            logger.warning(f"Brute force protection: Request blocked for {cache_key}")
            return False
        
        # Verificar intentos fallidos
        failed_attempts_key = f'{cache_key}_failed'
        failed_attempts = cache.get(failed_attempts_key, 0)
        
        if failed_attempts >= self.MAX_FAILED_ATTEMPTS:
            # Bloquear temporalmente
            cache.set(lockout_key, True, self.LOCKOUT_DURATION)
            logger.warning(
                f"Brute force protection: Account locked for {cache_key} "
                f"after {failed_attempts} failed attempts"
            )
            return False
        
        # Permitir request y aplicar throttling normal
        return super().allow_request(request, view)

    def record_failed_attempt(self, request):
        """
        Registra un intento fallido.
        Debe ser llamado manualmente desde la vista cuando falla la autenticación.
        """
        cache_key = self.get_cache_key(request, None)
        failed_attempts_key = f'{cache_key}_failed'
        failed_attempts = cache.get(failed_attempts_key, 0)
        cache.set(failed_attempts_key, failed_attempts + 1, 3600)  # 1 hora
        logger.warning(f"Failed login attempt recorded for {cache_key}")

    def reset_failed_attempts(self, request):
        """
        Resetea los intentos fallidos después de un login exitoso.
        Debe ser llamado manualmente desde la vista cuando la autenticación es exitosa.
        """
        cache_key = self.get_cache_key(request, None)
        failed_attempts_key = f'{cache_key}_failed'
        lockout_key = f'{cache_key}_lockout'
        cache.delete(failed_attempts_key)
        cache.delete(lockout_key)
        logger.info(f"Failed attempts reset for {cache_key}")
