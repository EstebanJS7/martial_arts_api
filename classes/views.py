from rest_framework import generics
from .models import Class, UserClassReservation
from .serializers import ClassSerializer, UserClassReservationSerializer

class ClassListView(generics.ListCreateAPIView):
    queryset = Class.objects.all()
    serializer_class = ClassSerializer

class ClassDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Class.objects.all()
    serializer_class = ClassSerializer

class UserClassReservationView(generics.ListCreateAPIView):
    queryset = UserClassReservation.objects.all()
    serializer_class = UserClassReservationSerializer
