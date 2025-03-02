from rest_framework import generics
from .models import BlogPost, Comment, Rating
from .serializers import BlogPostSerializer, CommentSerializer, RatingSerializer
from users.permissions import IsAuthorOrAdmin
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings
from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

@method_decorator(cache_page(settings.CACHE_TTL), name='list')
class BlogPostListView(generics.ListCreateAPIView):
    queryset = BlogPost.objects.all().order_by('-created_at')
    serializer_class = BlogPostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def perform_create(self, serializer):
        # Asigna el usuario autenticado como autor del BlogPost
        serializer.save(author=self.request.user)

@method_decorator(cache_page(settings.CACHE_TTL), name='retrieve')
class BlogPostDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
    permission_classes = [IsAuthorOrAdmin]

# Se elimina BlogPostCreateView para evitar redundancia

class CommentView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # Filtra los comentarios del BlogPost especificado por pk en la URL
        return Comment.objects.filter(blog_post_id=self.kwargs['pk'])

    def perform_create(self, serializer):
        # Corrige el nombre del campo: usa 'user' en lugar de 'author'
        serializer.save(user=self.request.user, blog_post_id=self.kwargs['pk'])

class RatingView(generics.CreateAPIView):
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, blog_post_id=self.kwargs['pk'])

    def get_queryset(self):
        return Rating.objects.filter(blog_post_id=self.kwargs['pk'], user=self.request.user)
