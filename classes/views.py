from rest_framework import generics
from .models import Class, UserClassReservation
from .serializers import ClassSerializer, UserClassReservationSerializer
from users.permissions import IsAdminUser, IsInstructorUser
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

class ClassCreateView(generics.CreateAPIView):
    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    permission_classes = [IsAdminUser | IsInstructorUser]

class ClassListView(generics.ListAPIView):
    queryset = Class.objects.all()
    serializer_class = ClassSerializer

class ClassDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    permission_classes = [IsAdminUser | IsInstructorUser]
    
class UserClassReservationCreateView(generics.CreateAPIView):
    queryset = UserClassReservation.objects.all()
    serializer_class = UserClassReservationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        class_reserved = serializer.validated_data['class_reserved']
        # Verificar si la cantidad de reservas alcanzó el límite de estudiantes permitidos
        if class_reserved.userclassreservation_set.count() >= class_reserved.max_students:
            raise ValidationError("Esta clase está completamente reservada.")
        serializer.save(user=self.request.user)
