from rest_framework import generics, permissions
from .models import Payment, QuotaConfig
from .serializers import PaymentSerializer, QuotaConfigSerializer
from users.permissions import IsAdminUser
from django_filters import rest_framework as filters
from .utils import create_next_month_payment, apply_user_payment, check_user_due_status
from django.http import JsonResponse
from users.models import CustomUser
from .filters import PaymentFilter

class PaymentListView(generics.ListAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = PaymentFilter
    
class UserPaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Retorna solo los pagos del usuario autenticado
        return Payment.objects.filter(user=self.request.user)

class PaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminUser]

class PaymentCreateView(generics.CreateAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        payment = serializer.save()
        # Crear automáticamente el pago del próximo mes para el usuario
        create_next_month_payment(payment.user)

class QuotaConfigView(generics.ListCreateAPIView):
    queryset = QuotaConfig.objects.all()
    serializer_class = QuotaConfigSerializer
    permission_classes = [IsAdminUser]

# Función para aplicar el pago a un usuario
def apply_user_payment_view(request, user_id, payment_amount):
    try:
        user = CustomUser.objects.get(id=user_id)
        apply_user_payment(user, payment_amount)
        return JsonResponse({"status": "success", "message": "Pago aplicado correctamente."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)

# Función para verificar el estado de pagos de un usuario
def check_user_due_status_view(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        status_info = check_user_due_status(user)
        return JsonResponse({"status": "success", "data": status_info})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
