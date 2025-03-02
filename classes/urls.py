# urls.py
from django.urls import path
from .views import (
    ClassCreateView, 
    MultiClassCreateView,
    ClassListView, 
    ClassDetailView,
    MultiClassUpdateView,
    UserClassReservationCreateView,
    UserClassReservationCancelView,
    UserClassReservationUpdateView,
    UpcomingClassesView
)

urlpatterns = [
    path('create/', ClassCreateView.as_view(), name='class-create'),
    path('create-multiple/', MultiClassCreateView.as_view(), name='class-create-multiple'),
    path('list/', ClassListView.as_view(), name='class-list'),
    path('<int:pk>/', ClassDetailView.as_view(), name='class-detail'),
    path('classes/bulk-update/', MultiClassUpdateView.as_view(), name='classes-bulk-update'),
    path('reserve/', UserClassReservationCreateView.as_view(), name='class-reserve'),
    path('reserve/<int:pk>/cancel/', UserClassReservationCancelView.as_view(), name='class-reservation-cancel'),
    path('reserve/<int:pk>/update/', UserClassReservationUpdateView.as_view(), name='class-reservation-update'),
    path('upcoming/', UpcomingClassesView.as_view(), name='upcoming-classes'),
]
