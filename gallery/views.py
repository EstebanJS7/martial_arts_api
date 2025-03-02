from rest_framework import generics, status
from .models import Gallery, GalleryItem
from .serializers import GallerySerializer, GalleryItemSerializer
from users.permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings
from rest_framework.pagination import PageNumberPagination

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

@method_decorator(cache_page(settings.CACHE_TTL), name='retrieve')
class GalleryDetailView(generics.RetrieveAPIView):
    queryset = Gallery.objects.all()
    serializer_class = GallerySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        gallery_items = GalleryItem.objects.filter(gallery=instance)
        gallery_items_serializer = GalleryItemSerializer(gallery_items, many=True)
        data = serializer.data
        data['items'] = gallery_items_serializer.data
        return Response(data, status=status.HTTP_200_OK)

# Vista para gestionar elementos multimedia
class GalleryItemListCreateView(generics.ListCreateAPIView):
    queryset = GalleryItem.objects.all()
    serializer_class = GalleryItemSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class GalleryItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = GalleryItem.objects.all()
    serializer_class = GalleryItemSerializer
    permission_classes = [IsAdminUser]
