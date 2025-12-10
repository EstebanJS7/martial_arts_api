from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Academy
from .serializers import AcademySerializer, AcademyCreateUpdateSerializer
from users.permissions import IsAdminUser


class AcademyListView(generics.ListCreateAPIView):
    """
    Vista para listar todas las academias (público) y crear nuevas (solo admin)
    """
    queryset = Academy.objects.filter(is_active=True)
    permission_classes = [AllowAny]  # Permitir lectura pública

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AcademyCreateUpdateSerializer
        return AcademySerializer

    def get_permissions(self):
        """
        Permitir GET a todos, pero POST solo a admins
        """
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdminUser()]
        return [AllowAny()]

    def get_queryset(self):
        """
        Si es admin, mostrar todas (incluyendo inactivas)
        Si es público, solo mostrar activas
        """
        queryset = Academy.objects.all()
        if not (self.request.user.is_authenticated and 
                (self.request.user.is_staff or 
                 (hasattr(self.request.user, 'userprofile') and 
                  self.request.user.userprofile.role == 'admin'))):
            queryset = queryset.filter(is_active=True)
        return queryset.order_by('name')


class AcademyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para ver, actualizar o eliminar una academia específica
    GET: Público
    PUT/PATCH/DELETE: Solo admin
    """
    queryset = Academy.objects.all()
    permission_classes = [AllowAny]  # Permitir lectura pública

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return AcademyCreateUpdateSerializer
        return AcademySerializer

    def get_permissions(self):
        """
        Permitir GET a todos, pero PUT/PATCH/DELETE solo a admins
        """
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [AllowAny()]

    def destroy(self, request, *args, **kwargs):
        """
        En lugar de eliminar, marcar como inactiva
        """
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(
            {'message': 'Academia marcada como inactiva'},
            status=status.HTTP_200_OK
        )

