from rest_framework import generics
from .models import Resource
from .serializers import ResourceSerializer
from users.permissions import IsAdminOrInstructor

class ResourceCreateView(generics.CreateAPIView):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [IsAdminOrInstructor]

class ResourceListView(generics.ListAPIView):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
