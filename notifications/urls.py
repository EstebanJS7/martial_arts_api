from django.urls import path

from .views import (
    NotificationListView,
    NotificationMarkReadView,
    UserNotificationPreferenceView,
)

urlpatterns = [
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/mark-read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('notifications/preferences/', UserNotificationPreferenceView.as_view(), name='notification-preferences'),
]







