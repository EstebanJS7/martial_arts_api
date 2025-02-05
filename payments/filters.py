import django_filters
from .models import Payment

class PaymentFilter(django_filters.FilterSet):
    user = django_filters.CharFilter(field_name="user__email", lookup_expr='icontains')
    date_payment = django_filters.DateFromToRangeFilter(field_name="date_payment")

    class Meta:
        model = Payment
        fields = ['user', 'date_payment']
