from django.urls import path
from .views import PaymentCreateView, PaymentListView, PaymentDetailView

urlpatterns = [
    path('create/', PaymentCreateView.as_view(), name='payment-create'),
    path('list/', PaymentListView.as_view(), name='payment-list'),
    path('<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
]