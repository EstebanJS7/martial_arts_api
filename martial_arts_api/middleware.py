"""
Middleware personalizado para manejar healthcheck sin redirecciones.
"""
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class HealthCheckMiddleware(MiddlewareMixin):
    """
    Middleware que intercepta peticiones a /health y /health/ 
    antes de que CommonMiddleware las redirija.
    """
    
    def process_request(self, request):
        # Interceptar peticiones a /health (con o sin barra final)
        if request.path in ['/health', '/health/']:
            return JsonResponse({
                "status": "healthy",
                "service": "martial_arts_api"
            }, status=200)
        return None

