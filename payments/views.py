from datetime import date, datetime
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
    PaymentApplySerializer,
    PaymentDashboardSerializer,
    PaymentTrendSerializer,
    TopPayerSerializer,
    PaymentMethodDistributionSerializer,
    PaymentStatsSerializer
)
from .services import PaymentService, PaymentDashboardService
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


# -------------------------------
# Endpoints para Dashboard de Pagos
# -------------------------------

class PaymentDashboardView(APIView):
    """
    Vista para obtener datos del dashboard de pagos.
    Acceso solo para administradores e instructores.
    """
    permission_classes = [permissions.IsAdminUser | permissions.IsAuthenticated]

    def has_permission(self, request, view):
        # Solo admin o instructor pueden acceder al dashboard
        return request.user.is_staff or (hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'instructor')

    def get(self, request):
        try:
            # Obtener parámetros de filtro desde query params
            period_months = request.query_params.get('period', 6)
            try:
                period_months = int(period_months)
            except ValueError:
                period_months = 6
            
            user_email = request.query_params.get('user_email', None)
            start_date = request.query_params.get('start_date', None)
            end_date = request.query_params.get('end_date', None)
            payment_method = request.query_params.get('payment_method', None)
            
            # Convertir fechas si se proporcionan
            if start_date:
                try:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                except ValueError:
                    start_date = None
            
            if end_date:
                try:
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                except ValueError:
                    end_date = None
            
            # Obtener datos del dashboard con filtros
            dashboard_data = PaymentDashboardService.get_dashboard_overview(
                period_months=period_months,
                user_email=user_email,
                start_date=start_date,
                end_date=end_date,
                payment_method=payment_method
            )
            
            # Obtener tendencias con filtros
            trends = PaymentDashboardService.get_payment_trends(
                period_months=period_months,
                user_email=user_email,
                payment_method=payment_method
            )
            
            # Obtener top pagadores con filtros
            top_payers = PaymentDashboardService.get_top_payers(
                limit=10,
                user_email=user_email,
                payment_method=payment_method
            )
            
            # Obtener distribución por métodos de pago (sin filtros de método aquí)
            payment_methods = PaymentDashboardService.get_payment_methods_distribution()
            
            response_data = {
                'overview': dashboard_data,
                'trends': trends,
                'top_payers': top_payers,
                'payment_methods': payment_methods
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"detail": f"Error al obtener datos del dashboard: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentStatsView(APIView):
    """
    Vista para obtener estadísticas mensuales de pagos.
    Acceso solo para administradores e instructores.
    """
    permission_classes = [permissions.IsAdminUser | permissions.IsAuthenticated]

    def has_permission(self, request, view):
        return request.user.is_staff or (hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'instructor')

    def get(self, request):
        try:
            year = request.query_params.get('year')
            month = request.query_params.get('month')
            
            if not year or not month:
                return Response(
                    {"detail": "Los parámetros 'year' y 'month' son requeridos"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                year = int(year)
                month = int(month)
            except ValueError:
                return Response(
                    {"detail": "Los parámetros 'year' y 'month' deben ser números válidos"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Obtener estadísticas del mes
            stats = PaymentDashboardService.get_monthly_stats(year, month)
            
            if not stats:
                return Response(
                    {"detail": "No se encontraron estadísticas para el período especificado"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"detail": f"Error al obtener estadísticas: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentTrendsView(APIView):
    """
    Vista para obtener tendencias de pagos.
    Acceso solo para administradores e instructores.
    """
    permission_classes = [permissions.IsAdminUser | permissions.IsAuthenticated]

    def has_permission(self, request, view):
        return request.user.is_staff or (hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'instructor')

    def get(self, request):
        try:
            period = request.query_params.get('period', 6)
            
            try:
                period = int(period)
            except ValueError:
                period = 6
            
            # Obtener tendencias
            trends = PaymentDashboardService.get_payment_trends(period)
            
            return Response(trends, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"detail": f"Error al obtener tendencias: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
