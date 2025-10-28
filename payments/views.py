from datetime import date
from decimal import Decimal
from django.http import JsonResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Prefetch
from django_filters.rest_framework import DjangoFilterBackend

from .models import Payment, QuotaConfig, PaymentTransaction
from .serializers import (
    PaymentSerializer, 
    PaymentCreateSerializer,
    QuotaConfigSerializer, 
    PaymentApplySerializer
)
from .services import PaymentService
from users.models import CustomUser
from .utils import create_next_month_payment
from .filters import PaymentFilter
from rest_framework.generics import ListAPIView
from .serializers import PaymentTransactionSerializer

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# -------------------------------
# Endpoints para administración de pagos (para administradores)
# -------------------------------

class PaymentListView(generics.ListAPIView):
    """
    Lista todos los pagos. Acceso restringido a administradores.
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = PaymentFilter
    
    def get_queryset(self):
        # Optimización: Usar select_related para cargar el usuario en una sola consulta
        # y prefetch_related para cargar las transacciones relacionadas
        return Payment.objects.select_related('user').prefetch_related(
            Prefetch('transactions', queryset=PaymentTransaction.objects.order_by('-transaction_date'))
        ).order_by('-due_date')


class PaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Permite ver, actualizar o eliminar un pago específico. Acceso solo para administradores.
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        return Payment.objects.select_related('user').prefetch_related(
            'transactions'
        )


class PaymentCreateView(generics.CreateAPIView):
    """
    Permite crear un nuevo pago. Tras la creación, se crea automáticamente el pago del próximo mes para el usuario.
    Acceso restringido a administradores e instructores.
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentCreateSerializer
    permission_classes = [permissions.IsAdminUser | permissions.IsAuthenticated]

    def has_permission(self, request, view):
        # Solo admin o instructor pueden crear pagos
        return request.user.is_staff or (hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'instructor')

    def perform_create(self, serializer):
        payment = serializer.save()
        # Crear automáticamente el pago del próximo mes para el usuario
        create_next_month_payment(payment.user)


class QuotaConfigView(generics.RetrieveUpdateDestroyAPIView):
    """
    Permite listar, crear, actualizar y eliminar configuraciones de cuota.
    Acceso restringido a administradores.
    """
    queryset = QuotaConfig.objects.all()
    serializer_class = QuotaConfigSerializer
    permission_classes = [permissions.IsAdminUser]

class QuotaConfigListView(generics.ListCreateAPIView):
    """
    Permite listar y crear configuraciones de cuota.
    Acceso restringido a administradores.
    """
    queryset = QuotaConfig.objects.all()
    serializer_class = QuotaConfigSerializer
    permission_classes = [permissions.IsAdminUser]


# -------------------------------
# Endpoint para verificar el estado de pagos de un usuario
# -------------------------------

def check_user_due_status_view(request, user_id):
    """
    Verifica si el usuario tiene pagos vencidos o cuál es el próximo pago pendiente.
    """
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Usuario no encontrado."}, status=404)

    due_payments = Payment.objects.filter(user=user, due_date__lt=date.today(), is_fully_paid=False)
    if due_payments.exists():
        data = {
            'status': 'overdue',
            'due_payments': [p.id for p in due_payments]
        }
    else:
        upcoming_payment = Payment.objects.filter(user=user, due_date__gte=date.today(), is_fully_paid=False).order_by('due_date').first()
        data = {
            'status': 'up_to_date',
            'next_payment_due_date': upcoming_payment.due_date if upcoming_payment else None
        }
    return JsonResponse({"status": "success", "data": data})


# -------------------------------
# Endpoint para aplicar pagos (usando la capa de servicios)
# -------------------------------

class ApplyUserPaymentView(APIView):
    """
    Aplica un pago a los pagos pendientes del usuario.
    Se valida que el monto sea positivo y que el usuario autenticado tenga permisos
    (debe ser el mismo usuario o tener privilegios de administrador).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id, payment_amount):
        # Validar mediante serializer que el monto es positivo
        payment_method = request.data.get('payment_method')
        description = request.data.get('description')
        serializer = PaymentApplySerializer(data={
            "user_id": user_id,
            "payment_amount": payment_amount
        })
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({"detail": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        # Verificar que el usuario autenticado sea el mismo o tenga privilegios (admin)
        if request.user != user and not request.user.is_staff:
            return Response({"detail": "No tienes permiso para aplicar pagos a este usuario."}, status=status.HTTP_403_FORBIDDEN)

        remaining_amount = PaymentService.apply_payment(
            user,
            serializer.validated_data["payment_amount"],
            payment_method=payment_method,
            description=description
        )
        data = {
            "status": "success",
            "message": "Pago aplicado correctamente.",
            "excess_amount": str(remaining_amount)
        }
        return Response(data, status=status.HTTP_200_OK)


# -------------------------------
# Endpoint para que el usuario consulte sus pagos
# -------------------------------

class UserPaymentListView(generics.ListAPIView):
    """
    Permite al usuario autenticado consultar sus pagos.
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = PaymentFilter
    
    def get_queryset(self):
        # Solo pagos del usuario autenticado
        return Payment.objects.filter(user=self.request.user).prefetch_related(
            Prefetch('transactions', queryset=PaymentTransaction.objects.order_by('-transaction_date'))
        ).order_by('-due_date')


class PaymentTransactionListView(ListAPIView):
    """
    Lista las transacciones de un pago específico.
    Acceso solo para el usuario dueño del pago, admin o instructor.
    """
    serializer_class = PaymentTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        payment_id = self.kwargs["payment_id"]
        try:
            payment = Payment.objects.get(pk=payment_id)
        except Payment.DoesNotExist:
            return PaymentTransaction.objects.none()
        user = self.request.user
        # Permitir solo si es dueño, admin o instructor
        if user == payment.user or user.is_staff or (hasattr(user, 'userprofile') and user.userprofile.role == 'instructor'):
            return PaymentTransaction.objects.filter(payment=payment).order_by('-transaction_date')
        return PaymentTransaction.objects.none()
