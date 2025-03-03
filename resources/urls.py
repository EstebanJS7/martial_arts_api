from django.urls import path
from .views import (
    ResourceListView,
    ResourceCreateView,
    ResourceDetailView,
    FeaturedResourcesView,
    ResourceTagListView,
    resource_download_view,
    resource_view_view
)

urlpatterns = [
    # Endpoints principales para recursos
    path('', ResourceListView.as_view(), name='resource-list'),
    path('create/', ResourceCreateView.as_view(), name='resource-create'),
    path('<int:pk>/', ResourceDetailView.as_view(), name='resource-detail'),
    
    # Endpoints para recursos destacados
    path('featured/', FeaturedResourcesView.as_view(), name='featured-resources'),
    
    # Endpoints para etiquetas
    path('tags/', ResourceTagListView.as_view(), name='resource-tags'),
    
    # Endpoint para descargas y vistas
    path('<int:pk>/download/', resource_download_view, name='resource-download'),
    path('<int:pk>/view/', resource_view_view, name='resource-view'),
]