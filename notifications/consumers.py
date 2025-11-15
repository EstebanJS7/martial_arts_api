from channels.generic.websocket import AsyncJsonWebsocketConsumer
import logging

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        try:
            # Aceptar la conexión primero
            await self.accept()
            
            # Grupo público inicial; luego podremos añadir grupos por usuario/rol
            self.group_name = 'notifications_public'
            
            # Solo agregar a grupos si channel_layer está disponible
            if self.channel_layer:
                await self.channel_layer.group_add(self.group_name, self.channel_name)
            
            # Grupo por usuario autenticado
            user = self.scope.get('user')
            if user and user.is_authenticated:
                self.user_group = f'user_{user.id}'
                if self.channel_layer:
                    await self.channel_layer.group_add(self.user_group, self.channel_name)
                logger.info(f'Usuario {user.id} conectado al WebSocket de notificaciones')
            else:
                logger.warning('Usuario no autenticado intentando conectar al WebSocket')
        except Exception as e:
            logger.error(f'Error al conectar WebSocket: {e}')
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, 'group_name') and self.channel_layer:
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
            user = self.scope.get('user')
            if user and user.is_authenticated and hasattr(self, 'user_group') and self.channel_layer:
                await self.channel_layer.group_discard(self.user_group, self.channel_name)
        except Exception as e:
            logger.error(f'Error al desconectar WebSocket: {e}')

    async def receive_json(self, content, **kwargs):
        # Eco mínimo para pruebas de conectividad
        await self.send_json({
            'type': 'echo',
            'payload': content,
        })

    async def notify(self, event):
        # Handler para mensajes de grupo
        await self.send_json(event.get('data', {}))


