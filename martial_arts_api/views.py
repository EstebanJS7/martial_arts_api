from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

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
            from blog.views import FeaturedBlogPostsView
            blog_view = FeaturedBlogPostsView()
            blog_view.request = request
            blog_response = blog_view.get(request)
            if hasattr(blog_response, 'data'):
                blog_posts = []
                for post in blog_response.data:
                    blog_posts.append({
                        'id': post['id'],
                        'title': post['title'],
                        'excerpt': post['content'][:150] + '...' if len(post['content']) > 150 else post['content'],
                        'author': post['author']['username'] if 'author' in post and 'username' in post['author'] else 'Anónimo',
                        'date': post['created_at'],
                        'imageUrl': post['image'] if post['image'] else '',
                        'url': f"/blog/{post['id']}"
                    })
                dashboard_data['blogPosts'] = blog_posts
        except Exception as e:
            logger.error(f"Error obteniendo entradas del blog: {str(e)}")
        
        return Response(dashboard_data) 