from django.urls import path
from . import views

urlpatterns = [
    path('', views.GalleryItemListView.as_view(), name='galleryitem-list'),
    path('<int:pk>/', views.GalleryItemDetailView.as_view(), name='galleryitem-detail'),
]