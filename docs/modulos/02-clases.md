# 02 — Clases (`classes`)

## Propósito

Núcleo operativo de la academia: creación y gestión de clases, reservas con control de concurrencia, asistencia (manual y por QR), listas de espera automatizadas, clases recurrentes desde plantillas, dashboards estadísticos y exportaciones PDF/Excel.

## Modelos y relaciones

| Modelo | Relaciones / campos clave |
|--------|---------------------------|
| `Class` | `instructor` FK usuario (`SET_NULL`); `date`, `duration` (default 1 h), `max_students`; `reservation_count` **desnormalizado** para evitar COUNT; tipo (`regular/intensive/private/seminar/exam`) y nivel (`kyu_a/kyu_b/dan/all`); cancelación (`is_cancelled`, `cancellation_reason`, `cancelled_by`, `cancelled_at`); contadores `attendance_count` / `no_show_count`; `qr_code_token` único nullable |
| `UserClassReservation` | `user` + `class_reserved` (**unique_together**); `is_cancelled`; timestamps. Cancelar = eliminar fila física |
| `ClassAttendance` | `class_reserved` + `user` (**unique_together**); `attended`, `check_in_time/out_time`, `notes`, `marked_by` (quien marcó) |
| `ClassTemplate` | Plantilla reutilizable: nombre, instructor, tipo/nivel (escala propia `beginner..all_levels`), duración, capacidad, prerrequisitos; baja lógica con `is_active` |
| `ClassWaitlist` | `user` + `class_reserved` (**unique_together**); `status`: `waiting/notified/converted/cancelled`; `position` auto-asignada; `notified_at`, `converted_at` |

### Asignación y compactación de posiciones en lista de espera

- `ClassWaitlist.save()` (altas): dentro de una transacción bloquea la fila de la clase con `select_for_update()` y asigna `posición = max(posiciones activas) + 1`. Cuentan como activas `waiting` **y** `notified` (un notificado sigue ocupando lugar de cola).
- `compact_positions(class_obj)` renumera 1..N las entradas activas preservando orden por posición, fecha de alta e id.
- `leave()` marca `cancelled` + compacta; `mark_converted()` marca `converted` con timestamp + compacta.
- La señal `post_delete(ClassWaitlist)` también compacta si alguien borra filas físicamente.

## Endpoints

Prefijo global: `/api/classes/`.

### Clases

| Método | Ruta | Permisos | Descripción |
|--------|------|----------|-------------|
| POST | `/create/` | Admin/Instructor | Crea clase individual con validaciones avanzadas (`ClassValidator`) |
| POST | `/create-multiple/` | Admin/Instructor | Crea varias clases; reporta errores por índice |
| GET | `/list/` | Autenticado | Próximas clases paginadas (`show_past=true` incluye pasadas) |
| GET | `/all/` | Autenticado | Historial de últimos 30 días |
| GET/PUT/PATCH/DELETE | `/{id}/` | Admin/Instructor | CRUD de clase con re-validación al actualizar |
| PUT | `/classes/bulk-update/` | Admin/Instructor | Actualización masiva transaccional (IDs inexistentes se omiten silenciosamente) |
| GET | `/upcoming/` | AllowAny (sin throttle) | Próximos 30 días; anota reserva del usuario autenticado |

### Reservas

| Método | Ruta | Permisos | Descripción |
|--------|------|----------|-------------|
| POST | `/reserve/` | Autenticado | Reserva atómica con `select_for_update` sobre la clase |
| DELETE | `/reserve/{id}/cancel/` | Dueño o staff | Cancela: decrementa contador bajo lock y elimina fila; dispara notificación a lista de espera |
| PUT/PATCH | `/reserve/{id}/update/` | Dueño o staff | Cambia la clase reservada ajustando ambos contadores |
| GET | `/reservations/my/` | Autenticado | Reservas activas propias con detalle de clase |
| GET | `/user-classes/` | Autenticado | Variante sin filtro de estado |

### Asistencia

| Método | Ruta | Permisos | Descripción |
|--------|------|----------|-------------|
| GET | `/{id}/attendance/` | Admin/Instructor | Lista asistencias completando reservas aún sin registro |
| POST | `/{id}/attendance/mark/` | Admin/Instructor | Marca/upsert asistencia de un estudiante (requiere reserva activa) |
| POST | `/{id}/attendance/bulk/` | Admin/Instructor | Marcación múltiple; errores por elemento |
| POST | `/{id}/attendance/check/` | Admin/Instructor | Garantiza registro de asistencia para cada reserva y recalcula contadores |
| GET | `/{id}/statistics/` | Admin/Instructor | Estadísticas puntuales de la clase |

### Plantillas y recurrencias

| Método | Ruta | Permisos | Descripción |
|--------|------|----------|-------------|
| GET/POST | `/templates/` | Admin/Instructor | Listar/crear plantillas activas |
| GET/PUT/PATCH/DELETE | `/templates/{id}/` | Admin/Instructor | Detalle; DELETE = baja lógica |
| POST | `/manage/recurring/` | Admin/Instructor | Genera clases recurrentes |
| POST | `/manage/reminders/` | Admin/Instructor | Dispara recordatorios manualmente (clase específica o proceso completo) |

### Estadísticas (Admin/Instructor)

`GET /dashboard/`, `/stats/monthly/`, `/stats/trends/`, `/stats/top-instructors/`, `/stats/popular-classes/`, `/stats/cancellations/` — todas delegan en `ClassDashboardService` con caché Redis de 15 min.

### Lista de espera

| Método | Ruta | Permisos | Descripción |
|--------|------|----------|-------------|
| GET | `/waitlist/?class_id=&status=` | Autenticado | Usuario normal ve solo sus entradas; admin/instructor ven todo |
| POST | `/waitlist/create/` | Autenticado | Alta en espera (body `{ "class_id": n }`) |
| DELETE | `/waitlist/{id}/delete/` | Dueño o admin/instructor | Cancela entrada (`leave()`) |
| POST | `/waitlist/{id}/convert/` | Solo dueño | Convierte notificación en reserva |

### QR check-in

| Método | Ruta | Permisos | Descripción |
|--------|------|----------|-------------|
| GET | `/{id}/qr-code/` | Admin/Instructor | Imagen PNG del QR (`{FRONTEND_URL}/checkin?token=...`) |
| GET | `/{id}/qr-data/` | Admin/Instructor | JSON `{token, qr_url, class_id, class_name, class_date}` |
| POST | `/qr-checkin/` | Autenticado | Body `{token}`; valida y registra check-in propio |

### Exportaciones (Admin/Instructor)

`GET ...?format=pdf|excel`: `/{id}/reports/attendance/`, `/reports/instructor/{id}/`, `/reports/occupancy/`, `/reports/waitlist/`, `/reports/cancellations/`. Implementadas con ReportLab (PDF) y openpyxl (Excel) en `export_service.py`.

## Reglas de negocio

### Flujo QR de check-in

1. El token se genera **perezosamente** con `secrets.token_urlsafe(32)` con formato `class_{id}_{token}` y es persistido (único). No hay endpoint de rotación: el token vive mientras exista la clase.
2. `ClassSerializer` **excluye** `qr_code_token` de toda respuesta (`exclude = ('qr_code_token',)`): exponerlo permitiría falsificar check-ins remotos. El token solo sale por `/qr-code/` y `/qr-data/`, ambos restringidos a admin/instructor.
3. Check-in válido si: clase no cancelada, momento actual ≤ fin de clase + 1 hora, y el usuario tiene reserva activa. Idempotente: segundo check-in devuelve error con el horario del primero.
4. Respuesta exitosa incluye campo aditivo `payment_status = {'is_overdue': bool, 'overdue_count': n}` calculado sobre pagos vencidos no pagados completamente (usa `is_overdue` marcada por tarea diaria y, como resguardo, `due_date < hoy`). Es **informativo**: no bloquea el check-in.

### Reservas concurrentes

`perform_create` bloquea la fila de la clase (`select_for_update`), valida que sea futura, que haya cupo y que no exista reserva previa, incrementa `reservation_count` con `F()` y refresca desde BD. El mismo patrón protege la conversión desde lista de espera y la reasignación de reservas.

### Automatización de lista de espera

1. Al **cancelarse una reserva** (o cualquier decremento de `reservation_count` detectado por la señal `post_save(Class)`), `_notify_waitlist_availability(clase)`: si hay cupo libre, promueve la primera entrada `waiting` a `notified` (con `notified_at`) y le envía notificación con payload `action='convert_to_reservation'`.
2. El usuario convierte vía `POST /waitlist/{id}/convert/` — exige estado `notified`, crea la reserva bajo lock de fila y marca `converted`.
3. **Expiración**: la tarea horaria `expire_stale_notified_waitlist_entries` (minuto 5) cancela las entradas `notified` con `notified_at` anterior a `now - WAITLIST_NOTIFIED_EXPIRY_HOURS` (default 24 h), compacta posiciones y vuelve a notificar al siguiente `waiting` si el cupo sigue libre. Es idempotente porque filtra siempre por estado vigente.
4. Si la **clase se cancela**, se notifica a todos los reservados y a las entradas activas de espera (`NotificationScheduler.send_class_cancellation_notifications`).

### Validaciones avanzadas (`ClassValidator`)

- Solapamiento de agenda del instructor con margen de 15 min → error.
- Capacidad por ubicación: suma de estudiantes de clases solapadas > 100 → error; entre 1 conflicto y el límite → advertencia no bloqueante.
- Clase en el pasado (más de 1 h) → error; duración fuera de [15 min, 8 h] → error.
- Equipamiento compartido en horario solapado: ≥3 conflictos → error; menos → advertencia.

### Clases recurrentes

`POST /manage/recurring/` acepta `template_id` **o** datos base explícitos (nombre e instructor obligatorios si no hay plantilla). Frecuencias `daily/weekly/monthly` con `days_of_week` (0=lunes…6=domingo, default: el día de `start_date`) y corte por `occurrences` (default 4) o `end_date`. Cada ocurrencia pasa por `ClassValidator`; las inválidas se reportan sin abortar el resto. Transacción única para todas las creaciones válidas.

## Señales y tareas

| Disparador | Efecto |
|-----------|--------|
| `post_save(UserClassReservation)` creado | Notifica al usuario ("Reserva confirmada") y al instructor |
| `post_save(UserClassReservation)` cancelado | Notifica a ambos + promueve lista de espera |
| `post_save(ClassAttendance)` | Recalcula `attendance_count`/`no_show_count` de la clase y notifica a alumno e instructor |
| `pre_save(Class)` | Estampa `cancelled_at` (o lo limpia si se re-habilita) y guarda valores previos para el post_save |
| `post_save(Class)` | Si el conteo de reservas bajó → promueve lista de espera; si pasó a cancelada → notificaciones masivas |
| `post_delete(ClassWaitlist)` | Compacta posiciones |
| Celery Beat: `classes.tasks.expire_stale_notified_waitlist_entries` cada hora | Expira cupos notificados vencidos (ver arriba) |

## Puntos de atención

- **Reingreso a lista de espera tras cancelar devuelve 400** (limitación conocida): `unique_together (user, class_reserved)` conserva la fila `cancelled`, así que un nuevo alta choca con la unicidad y cae en el handler de `IntegrityError` → `"No se pudo agregar a la lista de espera…"`. Reingresar requiere borrado físico de la fila vieja (solo posible desde admin o la señal post_delete).
- No se exige que la clase esté **llena** para entrar a la lista de espera: solo que no esté cancelada/pasada y que el usuario no tenga reserva ni entrada activa.
- El token QR no tiene rotación ni expiración propia: quien obtenga el token de un instructor puede hacer check-in hasta 1 h después del fin de la clase.
- `MultiClassUpdateView` omite silenciosamente IDs inexistentes dentro del bulk.
- Los contadores desnormalizados (`reservation_count`) dependen de que toda mutación pase por las vistas/servicios instrumentados; ediciones directas desde el admin pueden desincronizarlos (el healthcheck de asistencia recalcula los de asistencia, no los de reservas).
- `get_classes_by_type` del dashboard es heurístico (match por primera palabra del nombre contra plantillas) y no está expuesto por URL.
