from django.urls import path
from .views import ClassCreateView, ClassListView, ClassDetailView, UserClassReservationCreateView

urlpatterns = [
    path('create/', ClassCreateView.as_view(), name='class-create'),
    path('list/', ClassListView.as_view(), name='class-list'),
    path('<int:pk>/', ClassDetailView.as_view(), name='class-detail'),
    path('reserve/', UserClassReservationCreateView.as_view(), name='class-reserve'),
]