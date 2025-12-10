from django.urls import path
from .views import GalleryListCreateView, GalleryDetailView, GalleryItemListCreateView, GalleryItemDetailView

urlpatterns = [
    path('galleries/', GalleryListCreateView.as_view(), name='gallery-list-create'),
    path('galleries/<int:pk>/', GalleryDetailView.as_view(), name='gallery-detail'),
    path('items/', GalleryItemListCreateView.as_view(), name='galleryitem-list-create'),
    path('items/<int:pk>/', GalleryItemDetailView.as_view(), name='galleryitem-detail'),
]