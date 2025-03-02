from rest_framework import generics
from .models import Resource
from .serializers import ResourceSerializer
from users.permissions import IsAdminOrInstructor
from rest_framework.pagination import PageNumberPagination
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings

class ResourceCreateView(generics.CreateAPIView):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [IsAdminOrInstructor]

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

@method_decorator(cache_page(settings.CACHE_TTL), name='dispatch')
class ResourceListView(generics.ListAPIView):
    queryset = Resource.objects.all().order_by('-uploaded_at')
    serializer_class = ResourceSerializer
    pagination_class = StandardResultsSetPagination
