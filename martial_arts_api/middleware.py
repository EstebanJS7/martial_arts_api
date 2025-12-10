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
        try:
            # Interceptar peticiones a /health o /health/ (con o sin barra final)
            path = request.path
            normalized_path = path.rstrip('/')
            
            # Interceptar /health, /health/, o raíz
            if path == '/health' or path == '/health/' or normalized_path == '/health' or normalized_path == '':
                logger.info(f"HealthCheckMiddleware interceptando: {request.path}")
                # Crear respuesta directamente - esto evita que CommonMiddleware procese
                response = JsonResponse({
                    "status": "healthy",
                    "service": "martial_arts_api"
                }, status=200)
                return response
        except Exception as e:
            logger.error(f"Error en HealthCheckMiddleware.process_request: {e}")
        return None
    
    def process_response(self, request, response):
        try:
            # Si CommonMiddleware redirigió /health/ o raíz, interceptar aquí también
            path = request.path
            normalized_path = path.rstrip('/')
            
            # Interceptar cualquier redirección 301/302 relacionada con /health o raíz
            if (path == '/health' or path == '/health/' or normalized_path == '/health' or normalized_path == '') and response.status_code in [301, 302]:
                logger.warning(f"HealthCheckMiddleware interceptando redirección {response.status_code} para {request.path}")
                # Devolver 200 directamente en lugar de la redirección
                return JsonResponse({
                    "status": "healthy",
                    "service": "martial_arts_api"
                }, status=200)
            
            # También interceptar si la Location header apunta a /health
            if response.status_code in [301, 302]:
                location = response.get('Location', '')
                if location and ('/health' in location or location.endswith('/health') or location.endswith('/health/')):
                    logger.warning(f"HealthCheckMiddleware interceptando redirección a {location}")
                    return JsonResponse({
                        "status": "healthy",
                        "service": "martial_arts_api"
                    }, status=200)
        except Exception as e:
            logger.error(f"Error en HealthCheckMiddleware.process_response: {e}")
        
        return response

