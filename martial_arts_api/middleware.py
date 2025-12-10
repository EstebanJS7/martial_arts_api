"""
Middleware personalizado para manejar healthcheck sin redirecciones.
"""
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
import logging
import sys

# Configurar logger con salida a stdout para que aparezca en Railway
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[HealthCheckMiddleware] %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class HealthCheckMiddleware(MiddlewareMixin):
    """
    Middleware que intercepta peticiones a /health y /health/ 
    antes y después de que CommonMiddleware las procese.
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        logger.info("HealthCheckMiddleware inicializado correctamente")
    
    def process_request(self, request):
        try:
            path = request.path
            normalized_path = path.rstrip('/')
            method = request.method
            
            logger.info(f"process_request: path='{path}', normalized='{normalized_path}', method='{method}'")
            
            # Interceptar peticiones a /health o /health/ (con o sin barra final)
            if path == '/health' or path == '/health/' or normalized_path == '/health' or normalized_path == '':
                logger.info(f"✓ HealthCheckMiddleware INTERCEPTANDO: {request.path} -> devolviendo 200 OK")
                # Crear respuesta directamente - esto evita que CommonMiddleware procese
                response = JsonResponse({
                    "status": "healthy",
                    "service": "martial_arts_api"
                }, status=200)
                logger.info(f"✓ Respuesta creada: status=200, path={request.path}")
                return response
            else:
                logger.debug(f"  No interceptando: path='{path}' no coincide con /health")
        except Exception as e:
            logger.error(f"✗ ERROR en HealthCheckMiddleware.process_request: {e}", exc_info=True)
        return None
    
    def process_response(self, request, response):
        try:
            path = request.path
            normalized_path = path.rstrip('/')
            status_code = response.status_code
            
            logger.info(f"process_response: path='{path}', status={status_code}")
            
            # Si CommonMiddleware redirigió /health/ o raíz, interceptar aquí también
            if (path == '/health' or path == '/health/' or normalized_path == '/health' or normalized_path == '') and status_code in [301, 302]:
                location = response.get('Location', '')
                logger.warning(f"✗ REDIRECCIÓN DETECTADA: {status_code} para {request.path} -> Location: {location}")
                logger.warning(f"✓ HealthCheckMiddleware INTERCEPTANDO redirección -> devolviendo 200 OK")
                # Devolver 200 directamente en lugar de la redirección
                return JsonResponse({
                    "status": "healthy",
                    "service": "martial_arts_api"
                }, status=200)
            
            # También interceptar si la Location header apunta a /health
            if status_code in [301, 302]:
                location = response.get('Location', '')
                if location and ('/health' in location or location.endswith('/health') or location.endswith('/health/')):
                    logger.warning(f"✗ REDIRECCIÓN a /health detectada: {status_code} -> Location: {location}")
                    logger.warning(f"✓ HealthCheckMiddleware INTERCEPTANDO -> devolviendo 200 OK")
                    return JsonResponse({
                        "status": "healthy",
                        "service": "martial_arts_api"
                    }, status=200)
            
            if path == '/health' or path == '/health/':
                logger.info(f"  Respuesta final para {path}: status={status_code}")
        except Exception as e:
            logger.error(f"✗ ERROR en HealthCheckMiddleware.process_response: {e}", exc_info=True)
        
        return response

