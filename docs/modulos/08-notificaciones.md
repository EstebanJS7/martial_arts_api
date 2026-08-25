# 08 — Notificaciones (`notifications`)

## Propósito

Centro de notificaciones in-app con entrega en tiempo real por WebSocket: modelo persistente de notificaciones, consumer de Channels autenticado con JWT, preferencias por usuario y el planificador de recordatorios de clases que alimenta Celery Beat.

## Modelos y relaciones

| Modelo | Campos / reglas |
|--------|-----------------|
| `Notification` | `recipient` FK usuario **nullable** (null = global/pública); `title`, `message`; `type` enum: `info`, `success`, `warning`, `error`, `payment`, `class`; `data` JSON (payload contextual); `is_read`; orden `-created_at` |
| `UserNotificationPreference` | 1:1 con usuario (`related_name='notification_pref'`); flags `enabled` y `receive_realtime`, ambos default `True` |

## Endpoints REST

Prefijo global: `/api/`.

| Método | Ruta | Permisos | Descripción |
|--------|------|----------|-------------|
| GET | `/notifications/` | Autenticado | Notificaciones propias + globales (`recipient IS NULL`) |
| POST | `/notifications/mark-read/` | Autenticado | Body `{"ids": [..]}`; solo marca las del propio usuario |
| GET/PUT/PATCH | `/notifications/preferences/` | Autenticado | Preferencias propias (creadas on-demand) |

## Canal WebSocket

### Ruta y stack

- Ruta: **`/ws/notifications/`** (`notifications/routing.py`, montada desde `martial_arts_api/routing.py`).
- ProtocolTypeRouter en `asgi.py`: HTTP → healthcheck ASGI + Django; WebSocket → `JWTAuthMiddlewareStack(URLRouter(...))`.

### Middleware JWT (`JWTAuthMiddleware`)

Orden de extracción del token:

1. Query string: `?token=<jwt>`.
2. Header: `Authorization: Bearer <jwt>`.

Validación: `UntypedToken(token)` (firma + expiración de SimpleJWT) y decodificación manual HS256 con `SECRET_KEY` para extraer `user_id`. Sin token o token inválido → `AnonymousUser`.

**Tradeoff documentado del token por query string**: los WebSockets de navegador no permiten setear headers custom, de ahí el parámetro `?token=`. El costo es que la URL completa (con el access token) puede aparecer en logs de servidor/proxy e historial; mitígalo el hecho de que se usa el access token de corta vida (60 min) y no el refresh. El header Bearer sigue soportado para clientes nativos.

### Consumer (`NotificationConsumer`)

- `connect()`: acepta siempre la conexión; se une al grupo público `notifications_public` y, si hay usuario autenticado, a `user_{id}`. Conexiones anónimas quedan solo en el grupo público (se loguea warning, no se cierra).
- `notify(event)`: handler que reenvía a cada socket el JSON publicado al grupo.
- `receive_json`: eco mínimo para pruebas de conectividad.

## Servicios de envío

| Función | Comportamiento |
|---------|----------------|
| `notify_user(user_id, data)` | Publica por channel layer al grupo `user_{id}` o al público |
| `create_and_notify(recipient_id, title, message, ntype, payload)` | **Persiste** la `Notification` y luego emite por WS con `{id, title, message, type, data, created_at}` |

Toda la app usa `create_and_notify` (clases, pagos, exámenes, listas de espera): un único punto donde nacen las notificaciones.

## Tareas programadas (Celery)

| Tarea | Cadencia (Beat) | Qué hace |
|-------|------------------|----------|
| `send_class_reminders_task` | Cada 15 minutos | Ejecuta el proceso completo de recordatorios |
| `send_24h_reminders` / `send_1h_reminders` / `send_attendance_reminders` | No están en Beat (disparo manual/on-demand) | Versiones individuales |

Ventanas de `process_all_reminders()` (`NotificationScheduler`):

| Recordatorio | Ventana respecto a ahora | Destinatarios |
|--------------|--------------------------|---------------|
| Clase mañana (24 h) | inicio entre 23.5 h y 24.5 h | Usuarios con reserva activa |
| Clase en 1 hora | inicio entre 30 min y 90 min | Ídem |
| Marcar asistencia | clases terminadas entre hace 2 h y 1 h con reservas sin asistencia registrada | Instructor de la clase |

## Reglas de negocio

- Las notificaciones globales (`recipient=null`) las ven todos los usuarios autenticados en el listado REST; por WS hoy solo existen los grupos `user_{id}` y el público.
- El marcado de lectura es masivo pero acotado: `filter(id__in=ids, recipient=request.user)` — no puede marcar ajenas.
- La cancelación de una clase genera notificaciones a reservados y lista de espera (ver [02-clases](02-clases.md)); la promoción de lista de espera usa `action='convert_to_reservation'` como contrato para el botón del frontend.

## Puntos de atención

- **Caveat conocido de deduplicación**: las ventanas de recordatorio duran ~1 hora y Beat corre cada 15 minutos → cada clase/reserva elegible recibe **hasta 4 copias** del recordatorio 24 h y del de 1 h (y del de asistencia). No existe marca de "ya enviado" ni dedupe por payload (los comentarios del código lo reconocen). Mismo patrón en pagos vencidos (un aviso diario por deuda). Es el comportamiento actual, aceptado para el alcance del proyecto.
- **Preferencias ignoradas**: `enabled` / `receive_realtime` se exponen y persisten, pero `create_and_notify` no las consulta — ningún flujo filtra según preferencias hoy. Deuda funcional declarada.
- El middleware WS valida firma/expiración pero **no consulta la blacklist** de refresh tokens: un access token ya emitido sigue válido en el WS hasta expirar aunque el usuario haya cerrado sesión.
- Conexiones anónimas son aceptadas al grupo público: si algún día se publican datos sensibles por ese grupo, habría que rechazar el handshake sin usuario.
