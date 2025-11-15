from django.urls import path

from notifications.routing import websocket_urlpatterns as notifications_ws

websocket_urlpatterns = [
    *notifications_ws,
]







