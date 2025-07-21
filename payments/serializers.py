from rest_framework import serializers
from .models import Payment, QuotaConfig, PaymentTransaction

class PaymentSerializer(serializers.ModelSerializer):
    payment_method = serializers.CharField(source='transactions.first.payment_method', read_only=True)
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('date_payment', 'is_paid', 'is_fully_paid', 'amount_paid')


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
