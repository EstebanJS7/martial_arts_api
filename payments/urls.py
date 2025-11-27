from django.urls import path
from .views import (
    ApplyUserPaymentView,
    PaymentListView,
    PaymentDetailView,
    PaymentCreateView,
    QuotaConfigView,
    QuotaConfigListView,
    check_user_due_status_view,
    UserPaymentListView,
    PaymentTransactionListView,
    PaymentDashboardView,
    PaymentStatsView,
    PaymentTrendsView,
    PaymentStatusExportView
)

urlpatterns = [
    # Endpoint para aplicar pagos
    path('apply-payment/<int:user_id>/<str:payment_amount>/', ApplyUserPaymentView.as_view(), name='apply-payment'),
    
    # Endpoints para gestionar pagos (generalmente para administradores)
    path('list/', PaymentListView.as_view(), name='payment-list'),
    path('detail/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('create/', PaymentCreateView.as_view(), name='payment-create'),
    
    # Endpoints para configurar o consultar la cuota
    path('quota-config/', QuotaConfigListView.as_view(), name='quota-config-list'),
    path('quota-config/<int:pk>/', QuotaConfigView.as_view(), name='quota-config-detail'),
    
    # Endpoint para verificar el estado de pagos (vencidos o próximos)
    path('check-due-status/<int:user_id>/', check_user_due_status_view, name='check-due-status'),
    
    # Endpoint para que el usuario autenticado consulte sus pagos
    path('my-payments/', UserPaymentListView.as_view(), name='user-payments'),
    
    # Endpoints para Dashboard de Pagos (antes de rutas con parámetros dinámicos)
    path('dashboard/', PaymentDashboardView.as_view(), name='payment-dashboard'),
    path('stats/monthly/', PaymentStatsView.as_view(), name='payment-stats-monthly'),
    path('stats/trends/', PaymentTrendsView.as_view(), name='payment-trends'),
    
    # Endpoint para exportación de reportes (antes de rutas con parámetros dinámicos)
    path('reports/status/', PaymentStatusExportView.as_view(), name='payment-status-export'),
    
    # Endpoint para obtener las transacciones de un pago específico (al final, después de rutas específicas)
    path('<int:payment_id>/transactions/', PaymentTransactionListView.as_view(), name='payment-transactions'),
]
