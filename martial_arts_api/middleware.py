"""
Middleware personalizado para manejar healthcheck sin redirecciones.
"""
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)


class HealthCheckMiddleware(MiddlewareMixin):
    """
    Middleware que intercepta peticiones a /health y /health/ 
    antes y después de que CommonMiddleware las procese.
    """
    
    def process_request(self, request):
        # Normalizar el path (quitar barra final)
        path = request.path.rstrip('/')
        
        # Interceptar peticiones a /health (con o sin barra final) o raíz
        if path == '/health' or path == '':
            logger.info(f"HealthCheckMiddleware interceptando: {request.path} (normalizado: {path})")
            # Crear respuesta directamente
            response = JsonResponse({
                "status": "healthy",
                "service": "martial_arts_api"
            }, status=200)
            # Prevenir cualquier redirección
            if 'Location' in response:
                del response['Location']
            return response
        return None
    
    def process_response(self, request, response):
        # Si CommonMiddleware redirigió /health/ o raíz, interceptar aquí también
        path = request.path.rstrip('/')
        
        # Interceptar cualquier redirección 301/302 relacionada con /health o raíz
        if (path == '/health' or path == '') and response.status_code in [301, 302]:
            logger.warning(f"HealthCheckMiddleware interceptando redirección {response.status_code} para {request.path}")
            # Devolver 200 directamente en lugar de la redirección
            return JsonResponse({
                "status": "healthy",
                "service": "martial_arts_api"
            }, status=200)
        
        # También interceptar si la Location header apunta a /health
        if response.status_code in [301, 302]:
            location = response.get('Location', '')
            if '/health' in location or location.endswith('/'):
                logger.warning(f"HealthCheckMiddleware interceptando redirección a {location}")
                return JsonResponse({
                    "status": "healthy",
                    "service": "martial_arts_api"
                }, status=200)
        
        return response

