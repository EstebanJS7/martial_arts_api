from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
import requests
from django.conf import settings
from django.utils.html import strip_tags
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Vista de healthcheck para Railway y otros servicios de deployment.
    Siempre devuelve 200 OK para indicar que el servidor está funcionando.
    No verifica la base de datos para responder rápidamente.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Respuesta simple y rápida para healthcheck
        # No verificamos DB aquí para evitar timeouts
        return Response({
            "status": "healthy",
            "service": "martial_arts_api"
        }, status=status.HTTP_200_OK)

class DashboardView(APIView):
    """
    Vista para obtener todos los datos del dashboard en una sola llamada.
    Combina datos de clases, pagos, desempeño y blog.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        base_url = request.build_absolute_uri('/').rstrip('/')
        user = request.user
        
        # Inicializar datos del dashboard
        dashboard_data = {
            'upcomingClasses': [],
            'payments': [],
            'performanceStats': {},
            'blogPosts': []
        }
        
        # 1. Obtener próximas clases
        try:
            from classes.views import UpcomingClassesView
            classes_view = UpcomingClassesView()
            classes_view.request = request
            classes_response = classes_view.get(request)
            if classes_response.status_code == 200:
                dashboard_data['upcomingClasses'] = classes_response.data
        except Exception as e:
            logger.error(f"Error obteniendo clases: {str(e)}")
        
        # 2. Obtener pagos del usuario
        try:
            from payments.models import Payment
            recent_payments = Payment.objects.filter(user=user).order_by('-payment_date')[:5]
            
            payments_data = []
            for payment in recent_payments:
                payments_data.append({
                    'id': payment.id,
                    'concept': payment.concept,
                    'amount': float(payment.amount),
                    'date': payment.payment_date.strftime('%Y-%m-%d'),
                    'dueDate': payment.due_date.strftime('%Y-%m-%d') if payment.due_date else None,
                    'status': payment.status
                })
            
            dashboard_data['payments'] = payments_data
        except Exception as e:
            logger.error(f"Error obteniendo pagos: {str(e)}")
        
        # 3. Obtener estadísticas de desempeño
        try:
            from performance.views import UserPerformanceStatsView
            performance_view = UserPerformanceStatsView()
            performance_view.request = request
            performance_response = performance_view.get(request)
            if hasattr(performance_response, 'data'):
                dashboard_data['performanceStats'] = performance_response.data
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de desempeño: {str(e)}")
        
        # 4. Obtener entradas destacadas del blog
        try:
            from blog.models import BlogPost

            featured_posts = list(
                BlogPost.objects.filter(is_featured=True).order_by('-created_at')[:3]
            )
            if len(featured_posts) < 3:
                remaining = 3 - len(featured_posts)
                recent_posts = list(
                    BlogPost.objects.exclude(id__in=[post.id for post in featured_posts])
                    .order_by('-created_at')[:remaining]
                )
                featured_posts.extend(recent_posts)

            blog_posts = []
            for post in featured_posts:
                content = strip_tags(post.content or '')
                excerpt = f"{content[:150]}..." if len(content) > 150 else content
                blog_posts.append({
                    'id': post.id,
                    'title': post.title,
                    'excerpt': excerpt,
                    'author': post.author.get_full_name() or post.author.email or 'Anónimo',
                    'date': post.created_at.isoformat(),
                    'imageUrl': request.build_absolute_uri(post.image.url) if post.image else '',
                    'url': f"/blog/{post.id}"
                })

            # Fallback: si no se encontraron posts (por ejemplo en bases vacías),
            # consulta la API pública del blog para replicar el comportamiento de la landing.
            if not blog_posts:
                api_url = f"{base_url}/api/blog/posts/?page_size=3"
                api_response = requests.get(api_url, timeout=5)
                if api_response.status_code == 200:
                    payload = api_response.json()
                    posts_payload = payload.get('results', payload)
                    for post in posts_payload[:3]:
                        content = strip_tags(post.get('content', '') or '')
                        excerpt = f"{content[:150]}..." if len(content) > 150 else content
                        blog_posts.append({
                            'id': post.get('id'),
                            'title': post.get('title', ''),
                            'excerpt': excerpt,
                            'author': post.get('author_name') or 'Anónimo',
                            'date': post.get('created_at'),
                            'imageUrl': post.get('image') or '',
                            'url': f"/blog/{post.get('id')}"
                        })

            dashboard_data['blogPosts'] = blog_posts
        except Exception as e:
            logger.error(f"Error obteniendo entradas del blog: {str(e)}")
        
        return Response(dashboard_data) 