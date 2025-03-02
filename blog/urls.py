from django.urls import path
from .views import BlogPostListView, BlogPostDetailView, CommentView, RatingView, FeaturedBlogPostsView

urlpatterns = [
    # Endpoint para listar y crear BlogPosts
    path('posts/', BlogPostListView.as_view(), name='blogpost-list'),
    
    # Endpoint para detalle, actualización y eliminación de un BlogPost
    path('posts/<int:pk>/', BlogPostDetailView.as_view(), name='blogpost-detail'),
    
    # Endpoint para listar y crear comentarios de un BlogPost específico
    path('posts/<int:pk>/comments/', CommentView.as_view(), name='comment-list-create'),
    
    # Endpoint para asignar una puntuación (rating) a un BlogPost
    path('posts/<int:pk>/rate/', RatingView.as_view(), name='rating'),
    
    # Endpoint para obtener las entradas destacadas del blog
    path('featured/', FeaturedBlogPostsView.as_view(), name='featured-posts'),
]