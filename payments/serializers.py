from rest_framework import serializers
from .models import Payment, QuotaConfig, PaymentTransaction

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
    payment_method = serializers.CharField(write_only=True)
    external_transaction_id = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Payment
        fields = ['user', 'amount', 'description', 'payment_method', 'external_transaction_id']
        
    def create(self, validated_data):
        # Extraer datos que no pertenecen al modelo Payment
        payment_method = validated_data.pop('payment_method', None)
        external_transaction_id = validated_data.pop('external_transaction_id', None)
        
        # Crear el pago (due_date se calcula automáticamente en el modelo)
        payment = Payment.objects.create(**validated_data)
        
        # Crear la transacción asociada si se proporcionó información adicional
        if payment_method or external_transaction_id:
            PaymentTransaction.objects.create(
                payment=payment,
                amount=payment.amount,
                payment_method=payment_method,
                external_transaction_id=external_transaction_id,
                description=payment.description
            )
        
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
