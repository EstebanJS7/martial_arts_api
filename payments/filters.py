import django_filters
from .models import Payment

class PaymentFilter(django_filters.FilterSet):
    user = django_filters.CharFilter(field_name="user__email", lookup_expr='icontains')
    date_payment = django_filters.DateFromToRangeFilter(field_name="date_payment")
    due_date = django_filters.DateFromToRangeFilter(field_name="due_date")
    due_date__gte = django_filters.DateFilter(field_name="due_date", lookup_expr='gte')
    due_date__lte = django_filters.DateFilter(field_name="due_date", lookup_expr='lte')

    class Meta:
        model = Payment
        fields = ['user', 'date_payment', 'due_date', 'due_date__gte', 'due_date__lte']
