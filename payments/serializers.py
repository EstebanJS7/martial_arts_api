from rest_framework import serializers
from .models import Payment, QuotaConfig

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('date_payment', 'is_paid', 'is_fully_paid')

class QuotaConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotaConfig
        fields = '__all__'
