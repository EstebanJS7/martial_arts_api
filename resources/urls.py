from django.urls import path
from .views import ResourceCreateView, ResourceListView

urlpatterns = [
    path('create/', ResourceCreateView.as_view(), name='resource-create'),
    path('list/', ResourceListView.as_view(), name='resource-list'),
]