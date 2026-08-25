# 00 — Arquitectura general del backend

Documento de referencia transversal: stack tecnológico, estructura del proyecto, flujo de autenticación, modelo de roles y permisos, configuración destacada de `settings.py`, topología de despliegue y variables de entorno. Los detalles por dominio de negocio están en los documentos [01](01-usuarios.md) a [09](09-contacto.md).

## Propósito

Servir como mapa de entrada para revisores del proyecto (tesis) y desarrolladores nuevos: qué tecnología usa el sistema, cómo está organizado y qué decisiones de configuración sostienen el comportamiento observado en los módulos.

## Stack tecnológico

| Capa | Tecnología | Uso en el proyecto |
|------|------------|--------------------|
| Lenguaje / framework | Python 3.12 + Django 5.1 | Núcleo del backend |
| API | Django REST Framework | Serializadores, vistas genéricas, throttling, filtros `django_filters` |
| Autenticación | SimpleJWT + `token_blacklist` | JWT con rotación y blacklist de refresh tokens |
| Tiempo real | Channels 4 + `channels_redis` | WebSocket de notificaciones (`/ws/notifications/`) |
| Servidor ASGI | Daphne | Sirve HTTP y WebSocket en un solo proceso (`render.yaml`) |
| Tareas asíncronas | Celery (worker + beat) | Generación de cuotas, vencimientos, recordatorios, expiración de listas de espera |
| Base de datos | PostgreSQL | Producción sobre Supabase (con `sslmode=require`) vía `DATABASE_URL` |
| Caché / broker | Redis (django-redis) | Caché de dashboards, throttling y capa de canales; producción sobre Upstash (`rediss://` TLS) |
| Documentación API | drf-yasg | Swagger UI en `/swagger/`, Redoc en `/redoc/` |
| Archivos estáticos | WhiteNoise | Servido comprimido con manifest en producción |
| Almacenamiento multimedia | Cloudinary (opcional) o FileSystemStorage | Activado solo si las tres variables `CLOUDINARY_*` están presentes |
| Correo | SMTP (Gmail por defecto) | Reset de contraseña y formulario de contacto |
| Reportes | ReportLab (PDF) y openpyxl (Excel) | Exportaciones de clases y recibos de pago |
| QR | librería `qrcode` | Generación de imágenes PNG para check-in |

## Estructura del proyecto

```
martial_arts_api/
├── martial_arts_api/        # Configuración del proyecto Django
│   ├── settings.py          # Configuración única para dev/prod (por variables de entorno)
│   ├── celery.py            # Instancia Celery, autodescubrimiento de tareas
│   ├── asgi.py              # ProtocolTypeRouter: HTTP (healthcheck ASGI) + WS (JWT middleware)
│   ├── routing.py           # Agrega websocket_urlpatterns de notifications
│   ├── urls.py              # Rutas raíz, healthcheck, swagger/redoc
│   ├── views.py             # Healthcheck + DashboardView agregador
│   ├── pagination.py        # Standard/Small/LargeResultsSetPagination
│   └── tasks.py             # Tarea anual de generación de cuotas (proyecto)
├── users/                   # Usuarios, perfiles, roles, permisos, throttling de auth
├── classes/                 # Clases, reservas, asistencia, listas de espera, QR, exportaciones
├── payments/                # Cuotas, transacciones, recibos PDF, dashboards
├── performance/             # Cinturones, exámenes, eventos, estadísticas, progreso
├── blog/                    # Posts, comentarios, ratings, categorías y tags
├── gallery/                 # Galerías e ítems multimedia (imagen/video)
├── resources/               # Recursos didácticos con tracking de vistas/descargas
├── notifications/           # Modelo Notification, consumer WS, scheduler de recordatorios
├── contact/                 # Formulario de contacto y academias (dojos)
├── render.yaml              # Blueprint de despliegue (web + worker + beat + redis + db)
├── docker-compose*.yml      # Orquestación local / producción Docker
└── docs/modulos/            # Esta documentación
```

## Flujo de autenticación (JWT)

| Aspecto | Valor actual |
|---------|--------------|
| Identidad | Email único (`CustomUser.USERNAME_FIELD = 'email'`, sin username); backend propio `users.backends.EmailBackend` |
| Access token | 60 minutos |
| Refresh token | 24 horas |
| Rotación | `ROTATE_REFRESH_TOKENS = True`: cada `/api/token/refresh/` emite un refresh nuevo |
| Blacklist | `BLACKLIST_AFTER_ROTATION = True`: el refresh anterior queda invalidado al rotar |
| Logout | `POST /api/users/logout/` agrega el refresh enviado a la blacklist |

Rutas de emisión de tokens:

1. `POST /api/token/` — vista estándar de SimpleJWT (solo tokens).
2. `POST /api/users/login/` — login personalizado con anti-fuerza bruta: devuelve `access`, `refresh` y datos del usuario (rol, academia); tras 5 intentos fallidos por email/IP bloquea 15 minutos (`BruteForceProtectionThrottle`).

El frontend debe usar el par access/refresh y refrescar antes del vencimiento; después de un logout los refresh quedan en la tabla de blacklist.

## Roles y convenciones de permisos

Los roles viven en `UserProfile.role` (no en grupos de Django): `admin`, `instructor`, `student`. Los permisos reutilizables están en `users/permissions.py`:

| Clase | Autoriza |
|-------|----------|
| `IsAdminUser` | Superusuario, `is_staff`, o `userprofile.role == 'admin'` |
| `IsInstructorUser` | `userprofile.role == 'instructor'` |
| `IsAdminOrInstructor` | Ambos roles anteriores |
| `IsOwnerOrReadOnly` | Escritura solo al dueño del objeto (campo `user`) |
| `IsAuthorOrAdmin` | Escritura al autor del post o a `is_staff` |

Convenciones observadas:

- Lecturas públicas (landing): endpoints con `AllowAny` suelen desactivar además el throttling (`throttle_classes = []`).
- Operaciones administrativas de pagos y clases usan `IsAdminUser` o `IsAdminOrInstructor`.
- Vistas genéricas discriminan por método HTTP dentro de `get_permissions()` cuando GET es público pero la escritura no.

## Throttling (rate limiting)

Clases globales aplicadas por DRF: `UserRateThrottle` y `AnonRateThrottle`. El caché de contadores es Redis.

| Scope | Límite | Dónde se aplica |
|-------|--------|-----------------|
| `user` | 1000/hora | Global, usuarios autenticados |
| `anon` | 100/hora | Global, anónimos |
| `login` | 5/minuto | `LoginRateThrottle` en `/api/users/login/` |
| `register` | 3/hora | `RegisterRateThrottle` |
| `password_reset` | 3/hora | Solicitud de reset (clave: email) |
| `password_reset_confirm` | 5/hora | Confirmación de reset |
| `sensitive` | 20/hora | Aplicar pagos (`SensitiveEndpointThrottle`) |
| `brute_force` | 10/minuto + lockout | 5 fallos → bloqueo de 15 min |

## Settings destacados

### STORAGES y Cloudinary opcional

```python
STORAGES = {
    'default': MediaCloudinaryStorage si las tres vars CLOUDINARY_* están seteadas,
               si no FileSystemStorage,
    'staticfiles': WhiteNoise CompressedManifestStaticFilesStorage,
}
```

Sin Cloudinary, `MEDIA_URL = '/media/'` (servicio local válido solo en desarrollo). Con Cloudinary, `MEDIA_URL` apunta al dominio `res.cloudinary.com/<cloud>/`.

### CHANNEL_LAYERS

Si `REDIS_URL` trae esquema (`redis://` o `rediss://`) se usa tal cual — `rediss://` habilita TLS, requerido por Upstash. Solo si no hay esquema se arma la tupla `(host, puerto)` desde `REDIS_HOST`/`REDIS_PORT` saneados (el código limpia esquemas y puertos residuales que algunos entornos inyectan).

### Celery

Broker y result backend derivan de `REDIS_URL` forzando la BD `/0`; JSON como único formato de contenido. La zona horaria de beat sigue `TIME_ZONE`.

#### Cadencia de Celery Beat (`CELERY_BEAT_SCHEDULE`)

| Tarea | Cadencia | Función |
|-------|----------|---------|
| `martial_arts_api.tasks.generate_annual_payments_for_all_students` | 1 de enero 00:00 | Cuotas del año restante para estudiantes no exentos |
| `payments.tasks.generate_monthly_quotas` | Día 1 de cada mes, 06:05 | Cuota del mes (idempotente por usuario+período) |
| `payments.tasks.mark_overdue_payments` | Diaria, 06:45 | Marca/limpia `is_overdue` |
| `notifications.tasks.send_class_reminders_task` | Cada 15 minutos | Recordatorios 24 h, 1 h y de asistencia |
| `payments.tasks.notify_overdue_payments` | Diaria, 09:00 | Notifica pagos vencidos |
| `payments.tasks.remind_upcoming_due_payments` | Diaria, 09:15 | Cuotas que vencen exactamente en 3 días |
| `payments.tasks.generate_monthly_report` | Días 28–31, 10:00 | La tarea misma verifica que sea el último día del mes |
| `classes.tasks.expire_stale_notified_waitlist_entries` | Cada hora, minuto 5 | Expira cupos notificados de lista de espera |

## Topología de despliegue

Según `render.yaml` (Render Blueprint), con equivalentes documentados para proveedores externos ya soportados por `settings.py`:

```
                    ┌─────────────────────────────┐
   Frontend ──────► │ Web service (daphne, ASGI)  │◄──── healthcheck /health/
                    │ martial-arts-api            │
                    └───────┬───────────┬─────────┘
                            │           │
              ┌─────────────▼──┐   ┌────▼──────────────────┐
              │ Celery worker  │   │ Celery beat           │
              │ (tareas)       │   │ (programación)        │
              └───────┬────────┘   └────┬──────────────────┘
                      │   broker/backend │
              ┌───────▼──────────────────▼─────┐     ┌──────────────────────┐
              │ Redis (Upstash rediss:// TLS)  │     │ PostgreSQL (Supabase │
              │ cache + channels + celery      │     │ sslmode=require)     │
              └────────────────────────────────┘     └──────────────────────┘
```

- **Web**: `daphne -b 0.0.0.0 -p $PORT martial_arts_api.asgi:application`; `preDeployCommand` corre migraciones (y seed demo solo si `RUN_DEMO_SEED=true`). Healthcheck en `/health/`.
- **Healthcheck**: interceptado por un middleware ASGI propio antes de Django, responde 200 sin tocar middlewares ni base de datos; existe además una vista de respaldo en `martial_arts_api.views.health_check_view`.
- **Postgres**: el parser de `DATABASE_URL` detecta hosts `supabase` y agrega `sslmode=require` automáticamente.
- **Redis**: Upstash requiere TLS → la URL `rediss://` se propaga intacta a Channels, Celery y django-redis.
- Los planes `free` del blueprint (redis/postgres Render) son válidos para demostración; en producción real las variables apuntan a Supabase/Upstash sin cambiar código.

## Variables de entorno

| Variable | Requerida | Propósito |
|----------|-----------|-----------|
| `DEBUG` | No (default `False`) | Activa modo desarrollo: CORS abierto, media local, fallback de SECRET_KEY |
| `SECRET_KEY` | **Sí** en prod | Aborta el arranque si falta con `DEBUG=False` |
| `ALLOWED_HOSTS` | **Sí** en prod | Hosts separados por coma; se limpian protocolos/paths |
| `DATABASE_URL` | Sí en prod | Postgres (Supabase); SSL automático para hosts supabase |
| `REDIS_URL` | No (default `redis://localhost:6379/1`) | Compartido por Channels, Celery y caché; soporta `rediss://` |
| `CELERY_BROKER_URL` | No | Override del broker (default: `REDIS_URL` BD 0) |
| `CELERY_RESULT_BACKEND` | No | Override del backend de resultados |
| `CORS_ALLOWED_ORIGINS` | No en dev | Orígenes separados por coma en producción |
| `FRONTEND_URL` | No (default `http://localhost:5173`) | Base para links de reset de contraseña y URLs de QR |
| `WAITLIST_NOTIFIED_EXPIRY_HOURS` | No (default `24`) | Ventana para convertir un cupo notificado de lista de espera |
| `CLOUDINARY_CLOUD_NAME` | Condicional | Las tres juntas habilitan Cloudinary |
| `CLOUDINARY_API_KEY` | Condicional | Ídem |
| `CLOUDINARY_API_SECRET` | Condicional | Ídem |
| `EMAIL_BACKEND` | No (default SMTP) | Backend de correo |
| `EMAIL_HOST` / `EMAIL_PORT` | No (Gmail:587) | Servidor SMTP |
| `EMAIL_USE_TLS` | No (default `True`) | TLS para SMTP |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Sí para correo real | Credenciales SMTP |
| `DEFAULT_FROM_EMAIL` | No | Remitente visible |
| `TIME_ZONE` | No (default `UTC`) | Zona horaria; blueprint usa `America/Asuncion` |
| `LANGUAGE_CODE` | No (default `es-es`) | Idioma base |
| `SECURE_SSL_REDIRECT` | No (default `True` en prod) | Redirección HTTPS |
| `RUN_DEMO_SEED` / `ALLOW_DEMO_SEED` | No | Habilitan el seed de datos demo en preDeploy |

## Puntos de atención

- **Dos rutas de login coexisten** (`/api/token/` estándar y `/api/users/login/` personalizado). La personalizada es la que aporta lockout anti-fuerza bruta y devuelve rol/academia; conviene estandarizar el frontend en una sola.
- `ALLOWED_HOSTS` añade dos veces `healthcheck.railway.app` (residuo de un despliegue anterior en Railway); es inocuo pero es deuda de limpieza.
- El fallback de base de datos sin `DATABASE_URL` tiene credenciales hardcodeadas (`martial_user`/`abc12345`) — aceptable solo para desarrollo local.
- `CORS_ALLOWED_ORIGIN_REGEXES` conserva un ejemplo placeholder (`tu-dominio.com`) sin efecto real.
