from typing import Any, Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification


def notify_user(user_id: Optional[int], data: dict[str, Any]) -> None:
    """Envía un mensaje por WebSocket al usuario específico o al grupo público.

    Si user_id es None, envía al grupo público.
    """
    channel_layer = get_channel_layer()
    if user_id:
        group = f'user_{user_id}'
    else:
        group = 'notifications_public'

    async_to_sync(channel_layer.group_send)(group, {
        'type': 'notify',
        'data': data,
    })


def create_and_notify(recipient_id: Optional[int], title: str, message: str, ntype: str = 'info', payload: Optional[dict[str, Any]] = None) -> Notification:
    notification = Notification.objects.create(
        recipient_id=recipient_id,
        title=title,
        message=message,
        type=ntype,
        data=payload or {},
    )
    notify_user(recipient_id, {
        'id': notification.id,
        'title': notification.title,
        'message': notification.message,
        'type': notification.type,
        'data': notification.data,
        'created_at': str(notification.created_at),
    })
    return notification








