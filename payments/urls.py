from django.urls import path
from .views import PaymentListView, PaymentDetailView, PaymentCreateView, QuotaConfigView, apply_user_payment, check_user_due_status

urlpatterns = [
    path('list/', PaymentListView.as_view(), name='payment-list'),
    path('detail/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('create/', PaymentCreateView.as_view(), name='payment-create'),
    path('quota-config/', QuotaConfigView.as_view(), name='quota-config'),
    path('apply-payment/<int:user_id>/<int:payment_amount>/', apply_user_payment, name='apply-payment'),
    path('check-due-status/<int:user_id>/', check_user_due_status, name='check-due-status'),
]
