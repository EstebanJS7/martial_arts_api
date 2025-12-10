from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Avg, Count
from .models import BlogPost, Comment, Rating, Category, Tag
from .serializers import BlogPostSerializer, CommentSerializer, RatingSerializer, CategorySerializer, TagSerializer
from users.permissions import IsAuthorOrAdmin
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
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
    
    def get_throttles(self):
        """
        Deshabilitar throttling para GET requests (endpoints públicos).
        """
        if self.request.method == 'GET':
            return []  # Sin throttling para lectura pública
        return super().get_throttles()

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

class RatingView(generics.ListCreateAPIView):
    """
    Vista para listar y crear ratings de un post específico.
    Si el usuario ya tiene un rating, se actualiza en lugar de crear uno nuevo.
    """
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Rating.objects.filter(blog_post_id=self.kwargs['pk'], user=self.request.user)

    def perform_create(self, serializer):
        blog_post_id = self.kwargs['pk']
        user = self.request.user
        
        # Verificar si el usuario ya tiene un rating para este post
        existing_rating = Rating.objects.filter(
            blog_post_id=blog_post_id, 
            user=user
        ).first()
        
        if existing_rating:
            # Actualizar el rating existente
            existing_rating.score = serializer.validated_data['score']
            existing_rating.save()
        else:
            # Crear nuevo rating
            serializer.save(user=user, blog_post_id=blog_post_id)

class FeaturedBlogPostsView(generics.ListAPIView):
    """
    Vista para obtener las entradas destacadas del blog.
    """
    serializer_class = BlogPostSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        # Obtener las 3 entradas más recientes que estén marcadas como destacadas
        # Si no hay suficientes destacadas, completar con las más recientes
        featured_posts = BlogPost.objects.filter(
            is_featured=True
        ).order_by('-created_at')[:3]
        
        # Si no hay suficientes posts destacados, completar con los más recientes
        if featured_posts.count() < 3:
            # Excluir los posts que ya están en featured_posts
            featured_ids = [post.id for post in featured_posts]
            recent_posts = BlogPost.objects.exclude(
                id__in=featured_ids
            ).order_by('-created_at')[:3 - featured_posts.count()]
            
            # Combinar los queryset
            featured_posts = list(featured_posts) + list(recent_posts)
        
        return featured_posts


# Nuevas vistas para funcionalidad completa

class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para obtener, actualizar y eliminar un comentario específico.
    """
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Solo permitir acceso a comentarios del usuario autenticado
        return Comment.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        # Asegurar que solo el autor del comentario pueda actualizarlo
        if serializer.instance.user != self.request.user:
            return Response(
                {'error': 'No tienes permisos para actualizar este comentario'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer.save()

    def perform_destroy(self, instance):
        # Asegurar que solo el autor del comentario pueda eliminarlo
        if instance.user != self.request.user:
            return Response(
                {'error': 'No tienes permisos para eliminar este comentario'},
                status=status.HTTP_403_FORBIDDEN
            )
        instance.delete()


class RatingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para obtener, actualizar y eliminar un rating específico.
    """
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Solo permitir acceso a ratings del usuario autenticado
        return Rating.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        # Asegurar que solo el autor del rating pueda actualizarlo
        if serializer.instance.user != self.request.user:
            return Response(
                {'error': 'No tienes permisos para actualizar este rating'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer.save()

    def perform_destroy(self, instance):
        # Asegurar que solo el autor del rating pueda eliminarlo
        if instance.user != self.request.user:
            return Response(
                {'error': 'No tienes permisos para eliminar este rating'},
                status=status.HTTP_403_FORBIDDEN
            )
        instance.delete()


class BlogPostRatingsView(generics.ListAPIView):
    """
    Vista para obtener todos los ratings de un post específico.
    """
    serializer_class = RatingSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Rating.objects.filter(blog_post_id=self.kwargs['pk'])


@api_view(['GET'])
@permission_classes([AllowAny])
def blog_post_stats(request, pk):
    """
    Vista para obtener estadísticas de un post específico.
    """
    try:
        blog_post = BlogPost.objects.get(pk=pk)
    except BlogPost.DoesNotExist:
        return Response(
            {'error': 'Post no encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Calcular estadísticas
    ratings = Rating.objects.filter(blog_post=blog_post)
    comments = Comment.objects.filter(blog_post=blog_post)
    
    stats = {
        'post_id': blog_post.id,
        'post_title': blog_post.title,
        'total_ratings': ratings.count(),
        'average_rating': ratings.aggregate(avg_rating=Avg('score'))['avg_rating'] or 0,
        'total_comments': comments.count(),
        'rating_distribution': {
            '5_stars': ratings.filter(score=5).count(),
            '4_stars': ratings.filter(score=4).count(),
            '3_stars': ratings.filter(score=3).count(),
            '2_stars': ratings.filter(score=2).count(),
            '1_star': ratings.filter(score=1).count(),
        }
    }

    return Response(stats)


# Views para Category y Tag

class CategoryListView(generics.ListCreateAPIView):
    """
    Vista para listar y crear categorías.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination

class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para obtener, actualizar y eliminar una categoría específica.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class TagListView(generics.ListCreateAPIView):
    """
    Vista para listar y crear tags.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination

class TagDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para obtener, actualizar y eliminar un tag específico.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

@api_view(['GET'])
@permission_classes([AllowAny])
def category_posts(request, category_id):
    """
    Vista para obtener todos los posts de una categoría específica.
    """
    try:
        category = Category.objects.get(id=category_id)
        posts = BlogPost.objects.filter(category=category).order_by('-created_at')
        
        # Paginación manual
        page_size = int(request.GET.get('page_size', 10))
        page = int(request.GET.get('page', 1))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        posts_page = posts[start:end]
        serializer = BlogPostSerializer(posts_page, many=True)
        
        return Response({
            'category': CategorySerializer(category).data,
            'posts': serializer.data,
            'total_posts': posts.count(),
            'page': page,
            'page_size': page_size,
            'has_next': end < posts.count(),
            'has_previous': page > 1
        })
    except Category.DoesNotExist:
        return Response(
            {'error': 'Categoría no encontrada'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def tag_posts(request, tag_id):
    """
    Vista para obtener todos los posts de un tag específico.
    """
    try:
        tag = Tag.objects.get(id=tag_id)
        posts = BlogPost.objects.filter(tags=tag).order_by('-created_at')
        
        # Paginación manual
        page_size = int(request.GET.get('page_size', 10))
        page = int(request.GET.get('page', 1))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        posts_page = posts[start:end]
        serializer = BlogPostSerializer(posts_page, many=True)
        
        return Response({
            'tag': TagSerializer(tag).data,
            'posts': serializer.data,
            'total_posts': posts.count(),
            'page': page,
            'page_size': page_size,
            'has_next': end < posts.count(),
            'has_previous': page > 1
        })
    except Tag.DoesNotExist:
        return Response(
            {'error': 'Tag no encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
