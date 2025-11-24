from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import BeltRank
from .serializers import BeltRankSerializer, BeltRankCreateUpdateSerializer
from users.permissions import IsAdminUser


class BeltRankListView(generics.ListCreateAPIView):
    """
    Vista para listar todos los cinturones (público) y crear nuevos (solo admin)
    """
    queryset = BeltRank.objects.filter(is_active=True)
    permission_classes = [AllowAny]  # Permitir lectura pública

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BeltRankCreateUpdateSerializer
        return BeltRankSerializer

    def get_permissions(self):
        """
        Permitir GET a todos, pero POST solo a admins
        """
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdminUser()]
        return [AllowAny()]

    def get_queryset(self):
        """
        Si es admin, mostrar todos (incluyendo inactivos)
        Si es público, solo mostrar activos
        """
        queryset = BeltRank.objects.all()
        if not (self.request.user.is_authenticated and 
                (self.request.user.is_staff or 
                 (hasattr(self.request.user, 'userprofile') and 
                  self.request.user.userprofile.role == 'admin'))):
            queryset = queryset.filter(is_active=True)
        return queryset.order_by('order_number')


class BeltRankDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para ver, actualizar o eliminar un cinturón específico
    GET: Público
    PUT/PATCH/DELETE: Solo admin
    """
    queryset = BeltRank.objects.all()
    permission_classes = [AllowAny]  # Permitir lectura pública

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return BeltRankCreateUpdateSerializer
        return BeltRankSerializer

    def get_permissions(self):
        """
        Permitir GET a todos, pero PUT/PATCH/DELETE solo a admins
        """
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [AllowAny()]

    def destroy(self, request, *args, **kwargs):
        """
        En lugar de eliminar, marcar como inactivo
        """
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(
            {'message': 'Cinturón marcado como inactivo'},
            status=status.HTTP_200_OK
        )

