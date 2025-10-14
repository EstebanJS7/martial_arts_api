from django.urls import path
from .views import (
    BlogPostListView, BlogPostDetailView, CommentView, RatingView, FeaturedBlogPostsView,
    CommentDetailView, RatingDetailView, BlogPostRatingsView, blog_post_stats
)

urlpatterns = [
    # Endpoint para listar y crear BlogPosts
    path('posts/', BlogPostListView.as_view(), name='blogpost-list'),
    
    # Endpoint para detalle, actualización y eliminación de un BlogPost
    path('posts/<int:pk>/', BlogPostDetailView.as_view(), name='blogpost-detail'),
    
    # Endpoint para estadísticas de un BlogPost
    path('posts/<int:pk>/stats/', blog_post_stats, name='blogpost-stats'),
    
    # Endpoint para listar y crear comentarios de un BlogPost específico
    path('posts/<int:pk>/comments/', CommentView.as_view(), name='comment-list-create'),
    
    # Endpoint para gestionar un comentario específico (actualizar/eliminar)
    path('comments/<int:pk>/', CommentDetailView.as_view(), name='comment-detail'),
    
    # Endpoint para asignar una puntuación (rating) a un BlogPost
    path('posts/<int:pk>/rate/', RatingView.as_view(), name='rating'),
    
    # Endpoint para gestionar un rating específico (actualizar/eliminar)
    path('ratings/<int:pk>/', RatingDetailView.as_view(), name='rating-detail'),
    
    # Endpoint para obtener todos los ratings de un BlogPost
    path('posts/<int:pk>/ratings/', BlogPostRatingsView.as_view(), name='blogpost-ratings'),
    
    # Endpoint para obtener las entradas destacadas del blog
    path('featured/', FeaturedBlogPostsView.as_view(), name='featured-posts'),
]