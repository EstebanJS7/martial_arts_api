from django.db import transaction as db_transaction
from rest_framework import serializers
from .models import Payment, QuotaConfig, PaymentTransaction, PaymentStats
from .services import generate_next_receipt_number

class PaymentSerializer(serializers.ModelSerializer):
    payment_method = serializers.CharField(source='transactions.first.payment_method', read_only=True)
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('date_payment', 'is_paid', 'is_fully_paid', 'amount_paid')

class PaymentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer específico para crear pagos desde el frontend.
    No requiere due_date ya que se calcula automáticamente en el modelo.
    """
    payment_method = serializers.ChoiceField(
        choices=PaymentTransaction.PAYMENT_METHOD_CHOICES,
        write_only=True
    )
    external_transaction_id = serializers.CharField(write_only=True, required=False)
    reference_number = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Payment
        fields = ['user', 'amount', 'description', 'payment_method', 'external_transaction_id', 'reference_number']

    def create(self, validated_data):
        # Extraer datos que no pertenecen al modelo Payment
        payment_method = validated_data.pop('payment_method', None)
        external_transaction_id = validated_data.pop('external_transaction_id', None)
        reference_number = validated_data.pop('reference_number', None)

        # Crear el pago (due_date y período se calculan automáticamente en el modelo)
        payment = Payment.objects.create(**validated_data)

        # Crear la transacción asociada si se proporcionó información adicional,
        # registrando quién la cargó (auditoría) y su número de recibo secuencial
        if payment_method or external_transaction_id:
            request = self.context.get('request')
            registered_by = getattr(request, 'user', None)
            with db_transaction.atomic():
                transaction_obj = PaymentTransaction.objects.create(
                    payment=payment,
                    amount=payment.amount,
                    payment_method=payment_method,
                    external_transaction_id=external_transaction_id,
                    reference_number=reference_number or None,
                    registered_by=registered_by if getattr(registered_by, 'is_authenticated', False) else None,
                    description=payment.description,
                    receipt_number=generate_next_receipt_number(),
                )

            # Si la transacción es por el monto completo del pago, marcar el pago como pagado
            if transaction_obj.amount >= payment.amount:
                payment.amount_paid = payment.amount
                payment.is_paid = True
                payment.is_fully_paid = True
                payment.save()

        return payment


class QuotaConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotaConfig
        fields = '__all__'


class PaymentTransactionSerializer(serializers.ModelSerializer):
    payment_method = serializers.CharField(read_only=True)
    class Meta:
        model = PaymentTransaction
        fields = '__all__'


class PaymentApplySerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    payment_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate_payment_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto del pago debe ser un valor positivo.")
        return value


class PaymentStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentStats
        fields = '__all__'


class PaymentDashboardSerializer(serializers.Serializer):
    """Serializer para datos del dashboard de pagos"""
    total_collected = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    overdue_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_count = serializers.IntegerField()
    collection_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    period = serializers.CharField()


class PaymentTrendSerializer(serializers.Serializer):
    """Serializer para tendencias de pagos"""
    month = serializers.CharField()
    total_collected = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_count = serializers.IntegerField()


class TopPayerSerializer(serializers.Serializer):
    """Serializer para top pagadores"""
    user__email = serializers.EmailField()
    user__first_name = serializers.CharField()
    user__last_name = serializers.CharField()
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expected = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_count = serializers.IntegerField()
    on_time_payments = serializers.IntegerField()
    score = serializers.DecimalField(max_digits=5, decimal_places=2)


class PaymentMethodDistributionSerializer(serializers.Serializer):
    """Serializer para distribución por método de pago"""
    payment_method = serializers.CharField()
    count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
