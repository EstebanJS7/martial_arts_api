from django.urls import path
from . import views

urlpatterns = [
    path('', views.ClassListView.as_view(), name='class-list'),
    path('<int:pk>/', views.ClassDetailView.as_view(), name='class-detail'),
    path('<int:pk>/reserve/', views.UserClassReservationView.as_view(), name='class-reservation'),
]