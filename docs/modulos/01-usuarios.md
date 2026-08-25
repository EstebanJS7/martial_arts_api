# 01 — Usuarios (`users`)

## Propósito

Gestiona la identidad de la plataforma: usuario con login por email, perfil extendido con rol y pertenencia a academia, registro/login/logout, ciclo completo de contraseñas (cambio propio y reset por email), administración de cuentas y listados de estudiantes para instructores.

## Modelos y relaciones

### `CustomUser` (AUTH_USER_MODEL)

- Hereda de `AbstractUser`; **elimina `username`** y usa `email` único como `USERNAME_FIELD`.
- `first_name` / `last_name` opcionales (50 chars).
- Manager propio `CustomUserManager.create_user(email, password)` que normaliza el email y hashea la contraseña.

### `UserProfile` (1:1 con `CustomUser`, creación automática por señal)

| Campo | Detalle |
|-------|---------|
| `role` | `admin` \| `instructor` \| `student` (default `student`), indexado |
| `belt_rank` | FK → `performance.BeltRank` (`SET_NULL`, nullable): cinturón actual |
| `dojo` | FK → `contact.Academy` (`SET_NULL`, related `students`): academia del usuario |
| `is_exempt` | Boolean: exento de pago de cuotas (afecta generación automática en `payments`) |
| `enrollment_date` | Fecha de alta, `auto_now_add` |
| Datos personales | dirección, bio, foto (`profile_pics/`), edad, fecha de nacimiento, género, ciudad/provincia/país/barrio, teléfono, contacto de emergencia, `social_media_links` JSON |

### Señales a nivel de app

1. `post_save(CustomUser)` → crea el `UserProfile` al crear usuario; en updates re-guarda el perfil existente.
2. `post_save(UserProfile)` → si el perfil es nuevo y `role == 'student'`, invoca `PaymentService.create_payments_for_remaining_year(user)` (generación anual inicial de cuotas). Los errores se loguean sin abortar la creación del perfil.

## Endpoints

Prefijo global: `/api/users/`.

| Método | Ruta | Permisos | Descripción |
|--------|------|----------|-------------|
| GET/PATCH | `/profile/` | Autenticado | Perfil propio; lectura completa, PATCH con campos protegidos |
| POST | `/register/` | AllowAny (throttle 3/h) | Registro público con validación de contraseña y datos de perfil obligatorios |
| POST | `/login/` | AllowAny (5/min + lockout) | Login personalizado; devuelve tokens + datos de usuario/rol/dojo |
| POST | `/logout/` | Autenticado | Blacklisteá el refresh token recibido en el body |
| GET/POST | `/admin/users/` | Admin | Listado/creación de perfiles |
| POST | `/password-reset/` | AllowAny (3/h por email) | Envía link `{FRONTEND_URL}/password-reset-confirm/{uid}/{token}` |
| POST | `/password-reset-confirm/` | AllowAny (5/h) | Recibe `token` formato `uid/token` + nueva contraseña (validada) |
| POST | `/change-password/` | Autenticado | Requiere `old_password` correcto y nueva contraseña validada |
| POST | `/admin/update-role/<id>/` | Admin | Cambia `role` entre los tres valores válidos |
| GET | `/admin/stats/` | Admin | Totales por rol, activos/inactivos, altas de últimos 30 días |
| POST | `/admin/activate/<id>/` | Admin | Reactiva cuenta |
| POST | `/admin/deactivate/<id>/` | Admin | Desactiva cuenta (no permite auto-desactivarse) |
| DELETE | `/admin/delete/<id>/` | Admin | Soft delete: `is_active=False` + email reescrito a `deleted_{id}_{email}` |
| GET | `/instructor/students/` | Admin o Instructor | Estudiantes: admin ve todos, instructor solo los de su dojo |
| GET | `/verify-token/` | Autenticado | Valida el access token y devuelve datos del usuario |
| GET | `/public/instructors/?limit=n` | AllowAny (sin throttle) | Instructores para landing (campos públicos) |
| GET | `/public/stats/` | AllowAny (sin throttle) | Conteos agregados para landing |

Además existen las rutas estándar de SimpleJWT en el proyecto raíz: `POST /api/token/` y `POST /api/token/refresh/`.

## Reglas de negocio

### Contraseñas

- **Registro**: validador propio `validate_password_custom` → mínimo 8 caracteres y no completamente numérica; confirmación `password2` obligatoria.
- **Cambio y reset**: usan el validador oficial de Django `validate_password(user=...)`, es decir la política de `AUTH_PASSWORD_VALIDATORS`: similitud con atributos del usuario, longitud mínima, contraseñas comunes y no totalmente numérica. Los errores se devuelven campo por campo (`password`: [...]).
- El reset **no revela** si el email existe: respuesta genérica en ambos casos.
- La confirmación espera `token = "{uid_b64}/{token}"` (el uid y token separados por `/`).

### Auto-edición de perfil (PATCH `/profile/`)

`UserProfileSerializer` expone `fields = '__all__'` pero declara `read_only_fields = ('user', 'role', 'is_exempt', 'enrollment_date')`: el dueño del perfil **no puede** auto-asignarse rol, exención ni alterar identidad o fecha de alta. El rol solo cambia vía `UpdateUserRoleView` de admin. Campos derivados expuestos en lectura: `dojo_name`, `dojo_id`, `dojo_data` (objeto completo), `belt_rank_name/id/data`.

### Registro

Requiere (además de email/nombres/contraseña): `dojo` (ID de academia **activa**), `belt_rank` (ID de cinturón **activo**), `city`, `address`, `phone_number`. Tras crear el usuario, asigna esos valores al perfil creado por la señal. Al quedar rol `student`, la señal dispara la generación de cuotas del año restante.

### Anti-fuerza bruta

`BruteForceProtectionThrottle` mantiene contador de fallos por email/IP en Redis (TTL 1 h). Al quinto fallo bloquea 15 minutos; un login exitoso resetea contador y lockout.

### Listado seguro de estudiantes

`InstructorStudentsView` serializa con `UserSerializer` cuyo field set es explícito `(id, email, first_name, last_name, is_active)` — nunca `__all__` sobre el modelo de usuario, para no exponer hash de contraseña ni campos internos.

## Señales y tareas

| Disparador | Efecto |
|-----------|--------|
| Creación de `CustomUser` | Crea su `UserProfile` |
| Creación de `UserProfile` con rol `student` | Genera cuotas del resto del año (ver [03-pagos](03-pagos.md)) |

Este módulo no define tareas Celery propias.

## Puntos de atención

- `DeleteUserView` reescribe el email para liberar la unicidad, pero el prefijo incluye el ID original: el dato queda recuperable manualmente. No hay restauración implementada.
- El fallback anti-DoeS del login (`UserProfile.DoesNotExist` → crear perfil) duplica lógica que ya cubre la señal; funciona pero es código defensivo redundante.
- `PublicInstructorSerializer` expone el email real de instructores en un endpoint público — decisión consciente para la landing, pero digna de revisar si se publica el sistema.
- La política de contraseñas difiere entre flujos (registro usa el validador simple propio; cambio/reset usan los validadores completos de Django). No es un bug, pero conviene unificar criterio en la defensa.
