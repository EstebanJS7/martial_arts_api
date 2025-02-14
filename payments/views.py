from rest_framework import generics
from .models import Payment
from .serializers import PaymentSerializer
from users.permissions import IsAdminUser
from django_filters import rest_framework as filters
from rest_framework import generics

class PaymentFilter(filters.FilterSet):
    user = filters.CharFilter(field_name="user__username", lookup_expr='icontains')
    date = filters.DateFromToRangeFilter(field_name="date")

    class Meta:
        model = Payment
        fields = ['user', 'date']

class PaymentListView(generics.ListAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = PaymentFilter

class PaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminUser]
    

class PaymentCreateView(generics.CreateAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminUser]
    

