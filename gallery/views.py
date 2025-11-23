from rest_framework import generics, status, permissions
from .models import Gallery, GalleryItem
from .serializers import GallerySerializer, GalleryItemSerializer
from users.permissions import IsAdminUser, IsAdminOrInstructor
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from django.db.models import Prefetch

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100

# Vista para gestionar galerías
@method_decorator(cache_page(settings.CACHE_TTL), name='list')
class GalleryListCreateView(generics.ListCreateAPIView):
    queryset = Gallery.objects.all()
    serializer_class = GallerySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.request.method == 'GET':
            permission_classes = [AllowAny]  # Permitir acceso público para lectura
        else:  # POST (create)
            permission_classes = [IsAdminOrInstructor]
        return [permission() for permission in permission_classes]
    
    def get_throttles(self):
        """
        Deshabilitar throttling para GET requests (endpoints públicos).
        """
        if self.request.method == 'GET':
            return []  # Sin throttling para lectura pública
        return super().get_throttles()

class GalleryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GallerySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        return Gallery.objects.prefetch_related(
            Prefetch('galleryitem_set', queryset=GalleryItem.objects.all().order_by('-uploaded_at'))
        ).all()
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.request.method == 'GET':
            permission_classes = [AllowAny]  # Permitir acceso público para lectura
        else:  # PUT, PATCH, DELETE
            permission_classes = [IsAdminOrInstructor]
        return [permission() for permission in permission_classes]
    
    def get_throttles(self):
        """
        Deshabilitar throttling para GET requests (endpoints públicos).
        """
        if self.request.method == 'GET':
            return []  # Sin throttling para lectura pública
        return super().get_throttles()

# Vista para gestionar elementos multimedia
class GalleryItemListCreateView(generics.ListCreateAPIView):
    queryset = GalleryItem.objects.all()
    serializer_class = GalleryItemSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.request.method == 'GET':
            permission_classes = [AllowAny]  # Permitir acceso público para lectura
        else:  # POST (create)
            permission_classes = [IsAdminOrInstructor]
        return [permission() for permission in permission_classes]
    
    def get_throttles(self):
        """
        Deshabilitar throttling para GET requests (endpoints públicos).
        """
        if self.request.method == 'GET':
            return []  # Sin throttling para lectura pública
        return super().get_throttles()

class GalleryItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = GalleryItem.objects.all()
    serializer_class = GalleryItemSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.request.method == 'GET':
            permission_classes = [AllowAny]  # Permitir acceso público para lectura
        else:  # PUT, PATCH, DELETE
            permission_classes = [IsAdminOrInstructor]
        return [permission() for permission in permission_classes]
    
    def get_throttles(self):
        """
        Deshabilitar throttling para GET requests (endpoints públicos).
        """
        if self.request.method == 'GET':
            return []  # Sin throttling para lectura pública
        return super().get_throttles()
