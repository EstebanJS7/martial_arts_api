from django.urls import path
from . import views

urlpatterns = [
    path('', views.ResourceListView.as_view(), name='resource-list'),
    path('<int:pk>/', views.ResourceDetailView.as_view(), name='resource-detail'),
]