from django.urls import path
from .views import (
    ApplyUserPaymentView,
    PaymentListView,
    PaymentDetailView,
    PaymentCreateView,
    QuotaConfigView,
    check_user_due_status_view,
    UserPaymentListView
)

urlpatterns = [
    # Endpoint para aplicar pagos
    path('apply-payment/<int:user_id>/<str:payment_amount>/', ApplyUserPaymentView.as_view(), name='apply-payment'),
    
    # Endpoints para gestionar pagos (generalmente para administradores)
    path('list/', PaymentListView.as_view(), name='payment-list'),
    path('detail/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('create/', PaymentCreateView.as_view(), name='payment-create'),
    
    # Endpoint para configurar o consultar la cuota
    path('quota-config/', QuotaConfigView.as_view(), name='quota-config'),
    
    # Endpoint para verificar el estado de pagos (vencidos o próximos)
    path('check-due-status/<int:user_id>/', check_user_due_status_view, name='check-due-status'),
    
    # Endpoint para que el usuario autenticado consulte sus pagos
    path('my-payments/', UserPaymentListView.as_view(), name='user-payments'),
]
