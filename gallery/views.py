from rest_framework import generics, status
from .models import Gallery, GalleryItem
from .serializers import GallerySerializer, GalleryItemSerializer
from users.permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

# Vista para gestionar galerías
class GalleryListCreateView(generics.ListCreateAPIView):
    queryset = Gallery.objects.all()
    serializer_class = GallerySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

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
