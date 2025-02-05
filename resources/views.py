from rest_framework import generics
from .models import Resource
from .serializers import ResourceSerializer
from users.permissions import IsAdminOrInstructor
from rest_framework.pagination import PageNumberPagination

class ResourceCreateView(generics.CreateAPIView):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [IsAdminOrInstructor]

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ResourceListView(generics.ListAPIView):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    pagination_class = StandardResultsSetPagination
