from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from .models import Resource, ResourceTag, ResourceType, ResourceCategory, ResourceLevel
from .serializers import (
    ResourceListSerializer, 
    ResourceDetailSerializer, 
    ResourceCreateUpdateSerializer,
    ResourceTagSerializer
)
from users.permissions import IsAdminOrInstructor

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

class ResourceListView(generics.ListAPIView):
    serializer_class = ResourceListSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'category', 'level', 'is_featured']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'views_count', 'downloads_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Resource.objects.all()
        
        # Filtrar por etiquetas si se proporciona
        tags = self.request.query_params.getlist('tags')
        if tags:
            queryset = queryset.filter(tags__id__in=tags).distinct()
            
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        return context

class ResourceCreateView(generics.CreateAPIView):
    queryset = Resource.objects.all()
    serializer_class = ResourceCreateUpdateSerializer
    permission_classes = [IsAuthenticated, IsAdminOrInstructor]
    parser_classes = [MultiPartParser, FormParser]
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

class ResourceDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Resource.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ResourceCreateUpdateSerializer
        return ResourceDetailSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        return context
    
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.increment_views()
        return super().get(request, *args, **kwargs)
    
    def check_object_permissions(self, request, obj):
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            # Verificar si el usuario es admin o instructor
            user_profile = getattr(request.user, 'userprofile', None)
            is_admin_or_instructor = (
                request.user.is_staff or 
                (user_profile and user_profile.role in ['admin', 'instructor']) or
                request.user == obj.author
            )
            if not is_admin_or_instructor:
                self.permission_denied(request)
        return super().check_object_permissions(request, obj)

class FeaturedResourcesView(generics.ListAPIView):
    serializer_class = ResourceListSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        return context
    
    @method_decorator(cache_page(settings.CACHE_TTL))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        return Resource.objects.filter(is_featured=True).order_by('-created_at')

class ResourceTagListView(generics.ListCreateAPIView):
    queryset = ResourceTag.objects.all()
    serializer_class = ResourceTagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def check_permissions(self, request):
        if request.method != 'GET':
            user_profile = getattr(request.user, 'userprofile', None)
            is_admin_or_instructor = (
                request.user.is_authenticated and 
                (request.user.is_staff or (user_profile and user_profile.role in ['admin', 'instructor']))
            )
            if not is_admin_or_instructor:
                self.permission_denied(request)
        return super().check_permissions(request)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resource_download_view(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    
    # Incrementar contador de descargas
    resource.increment_downloads()
    
    # Devolver la URL del archivo
    if resource.file:
        return Response({
            "download_url": request.build_absolute_uri(resource.file.url),
            "filename": resource.file.name.split('/')[-1],
            "file_size": resource.file_size
        })
    elif resource.url:
        return Response({
            "download_url": resource.url,
            "filename": resource.title,
            "file_size": None
        })
    else:
        return Response(
            {"detail": "Este recurso no tiene archivo o URL para descargar."},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resource_view_view(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    resource.increment_views()
    return Response({"detail": "Vista registrada correctamente."}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resource_stats_view(request):
    """
    Vista para obtener estadísticas de recursos.
    Solo accesible por administradores e instructores.
    """
    user_profile = getattr(request.user, 'userprofile', None)
    is_admin_or_instructor = (
        request.user.is_staff or 
        (user_profile and user_profile.role in ['admin', 'instructor'])
    )
    
    if not is_admin_or_instructor:
        return Response(
            {"detail": "No tienes permisos para ver estas estadísticas."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Calcular estadísticas
    total_resources = Resource.objects.count()
    total_views = Resource.objects.aggregate(total=Sum('views_count'))['total'] or 0
    total_downloads = Resource.objects.aggregate(total=Sum('downloads_count'))['total'] or 0
    featured_resources = Resource.objects.filter(is_featured=True).count()
    
    # Recursos por tipo
    resources_by_type = {}
    for type_choice in ResourceType.choices:
        count = Resource.objects.filter(type=type_choice[0]).count()
        resources_by_type[type_choice[1]] = count
    
    # Recursos por categoría
    resources_by_category = {}
    for category_choice in ResourceCategory.choices:
        count = Resource.objects.filter(category=category_choice[0]).count()
        resources_by_category[category_choice[1]] = count
    
    # Recursos más populares
    popular_resources = Resource.objects.order_by('-views_count')[:5]
    popular_resources_data = ResourceListSerializer(popular_resources, many=True).data
    
    stats = {
        'total_resources': total_resources,
        'total_views': total_views,
        'total_downloads': total_downloads,
        'featured_resources': featured_resources,
        'resources_by_type': resources_by_type,
        'resources_by_category': resources_by_category,
        'popular_resources': popular_resources_data,
    }
    
    return Response(stats, status=status.HTTP_200_OK)
