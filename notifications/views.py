from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.db.models import Q

from .models import Notification, UserNotificationPreference
from .serializers import (
    NotificationSerializer,
    NotificationReadSerializer,
    UserNotificationPreferenceSerializer,
)


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Notificaciones del usuario y públicas (recipient null)
        return Notification.objects.filter(Q(recipient=user) | Q(recipient__isnull=True))


class NotificationMarkReadView(generics.GenericAPIView):
    serializer_class = NotificationReadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data['ids']
        Notification.objects.filter(id__in=ids, recipient=request.user).update(is_read=True)
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class UserNotificationPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = UserNotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        pref, _ = UserNotificationPreference.objects.get_or_create(user=self.request.user)
        return pref









