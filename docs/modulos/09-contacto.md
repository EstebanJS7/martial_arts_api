# 09 — Contacto (`contact`)

## Propósito

Dos responsabilidades: recibir mensajes del formulario de contacto público (landing) y administrar el catálogo de academias/dojos que alimenta el registro de usuarios, los perfiles y la sección de ubicaciones.

## Modelos y relaciones

| Modelo | Campos / reglas |
|--------|-----------------|
| `ContactMessage` | `name`, `email`, `phone` (opcional), `message`, `is_read`, `created_at` |
| `Academy` | Nombre, dirección, teléfono, email, horario (texto), `latitude`/`longitude` (`DecimalField(9,6)`), `is_active`. Property `coordinates` → `[lat, lng]` para mapas. Referenciada por `UserProfile.dojo` (`related_name='students'`) |

## Endpoints

Prefijo global: `/api/contact/`.

| Método | Ruta | Permisos | Descripción |
|--------|------|----------|-------------|
| POST | `/` | AllowAny | Formulario de contacto público |
| GET | `/academies/` | AllowAny | Lista academias **activas** (admin/staff ven también inactivas) |
| POST | `/academies/` | Admin | Crear academia |
| GET | `/academies/{id}/` | AllowAny | Detalle público con coordenadas |
| PUT/PATCH/DELETE | `/academies/{id}/` | Admin | Edición; DELETE = baja lógica (`is_active=False`) |

## Reglas de negocio

### Formulario de contacto

1. Valida con `ContactMessageSerializer` (nombre, email válido, mensaje; teléfono opcional) → 400 con errores si falla.
2. Persiste siempre el mensaje en la base de datos.
3. Envía **dos correos de forma síncrona** dentro del request:
   - A todos los usuarios `is_staff=True and is_active=True` (si no hay ninguno, usa `EMAIL_HOST_USER`).
   - Confirmación automática al remitente.
4. Si el envío falla (SMTP caído, credenciales inválidas), se loguea el error y **se responde igualmente 201** — el mensaje quedó guardado; solo se pierde el correo.
5. No hay captcha ni throttling específico: aplica únicamente el throttle global anónimo (100/hora).

### Academias como catálogo maestro

El registro de usuarios exige un `dojo` activo (validación en `RegisterSerializer` de [01-usuarios](01-usuarios.md)), y el listado público alimenta la landing y el mapa de sucursales (`coordinates`). Desactivar una academia impide nuevos registros contra ella sin romper perfiles existentes (FK con `SET_NULL` desde el perfil).

## Señales y tareas

Ninguna. El envío de correo es directo (`send_mail`), sin Celery.

## Puntos de atención

- **Envío síncrono**: los dos `send_mail` bloquean el request HTTP (latencia SMTP sumada al tiempo de respuesta). Para volumen real convendría moverlo a una tarea Celery — hoy es deliberadamente simple.
- La respuesta 201 ante fallo de correo evita frustrar al visitante pero oculta el problema: solo queda evidencia en logs del servidor.
- `is_read` de `ContactMessage` existe en el modelo pero **no hay endpoint** que lo actualice: su gestión es exclusivamente vía Django Admin.
- El fallback a `EMAIL_HOST_USER` como destinatario asume que esa variable contiene un correo real (en Gmail sí); con otros proveedores podría no coincidir.
