from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
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
    filterset_fields = ['type', 'category', 'level', 'is_premium', 'is_featured']
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
        if request.method in ['PUT', 'PATCH', 'DELETE'] and not (
            request.user.is_staff or 
            request.user.is_instructor or 
            request.user == obj.author
        ):
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
            if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_instructor)):
                self.permission_denied(request)
        return super().check_permissions(request)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resource_download_view(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    
    # Verificar si el recurso es premium y si el usuario tiene acceso
    if resource.is_premium and not (request.user.is_staff or request.user.is_instructor or request.user.has_premium_access):
        return Response(
            {"detail": "Este recurso requiere acceso premium."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Incrementar contador de descargas
    resource.increment_downloads()
    
    # Devolver la URL del archivo
    if resource.file:
        return Response({"download_url": request.build_absolute_uri(resource.file.url)})
    elif resource.url:
        return Response({"download_url": resource.url})
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
