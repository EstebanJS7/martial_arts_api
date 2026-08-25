# 04 — Desempeño (`performance`)

## Propósito

Gestión de la progresión del estudiante: catálogo de cinturones con requisitos configurables, sesiones y resultados de examen (con promoción automática de cinturón), eventos y participaciones verificables, estadísticas de desempeño, y los endpoints de retención: progreso personal, alumnos en riesgo y habilitados para examen.

## Modelos y relaciones

| Modelo | Campos / relaciones clave |
|--------|---------------------------|
| `Discipline` | Nombre único de disciplina |
| `BeltRank` | `name` único, `order_number` único (1=Blanco…), `category` (`Kyu A`/`Kyu B`/`Dan`), **`required_classes` nullable default 20** editable desde el admin, `is_active`. Métodos `get_next_belt()` / `get_previous_belt()` por orden |
| `EvaluationParameter` | Parámetro rubricado (nombre, descripción, categoría libre) |
| `ExamSession` | `belt_rank` FK PROTECT (nullable por compatibilidad), `belt_level` texto heredado autocompletado en `save()`, `exam_date`, `created_by`, M2M `participants`, M2M `evaluation_parameters` |
| `ExamResult` | Único por `(exam_session, participant)`; `graded`, `passed`. `save()` detecta transición a aprobado → `update_user_belt()` |
| `ExamResultParameterScore` | Puntaje entero por `(exam_result, parameter)` |
| `EventCategory` | Categorías dinámicas de eventos (`is_active`) |
| `Event` | Evento externo con `is_verified`, `verified_by/at`, organizador, disciplinas y categorías M2M |
| `EventParticipation` | Único por `(event, user, event_category)`; resultado enum (`1st..5th`, `participation`, `exhibition`); verificación por admin |
| `PerformanceStatistics` | 1:1 con usuario; `classes_attended` + M2M de exámenes y participaciones; refrescada por señales |

### Semántica del conteo de asistencias

Tanto `PerformanceStatistics.update_statistics()` como el cálculo de progreso cuentan **asistencias reales**: `ClassAttendance.attended=True` en clases pasadas y no canceladas. Antes se contaban reservas activas, lo que inflaba la tasa cercana al 100 % aunque el alumno faltara.

## Endpoints

Prefijo global: `/api/performance/`.

| Método | Ruta | Permisos | Descripción |
|--------|------|----------|-------------|
| GET | `/belt-ranks/` | AllowAny | Lista cinturones activos ordenados; admin/staff ven también inactivos |
| POST | `/belt-ranks/` | Admin | Crear cinturón |
| GET | `/belt-ranks/{id}/` | AllowAny | Detalle público |
| PUT/PATCH/DELETE | `/belt-ranks/{id}/` | Admin | Edición; DELETE = baja lógica (`is_active=False`) |
| GET/POST | `/parameters/` | Admin/Instructor | Parámetros de evaluación |
| GET/PUT/PATCH/DELETE | `/parameters/{id}/` | Admin/Instructor | Detalle parámetro |
| GET/POST | `/exam-sessions/` | Admin/Instructor | Sesiones de examen; la creación valida participantes y genera resultados |
| GET/PUT/PATCH/DELETE | `/exam-sessions/{id}/` | Admin/Instructor | Detalle sesión |
| GET/POST | `/exam-results/` | Admin/Instructor | Calificaciones; filtro `?exam_session=` |
| GET/PUT/PATCH/DELETE | `/exam-results/{id}/` | Admin/Instructor | Detalle/edición de calificación |
| GET | `/my-exam-results/` | Autenticado | Resultados propios |
| GET | `/statistics/` | Autenticado | `PerformanceStatistics` propia |
| GET | `/user-stats/` | Autenticado | Panel propio: asistencia real, skill level, logros, progreso por categoría |
| GET | `/my-progress/` | Autenticado | Progreso hacia próximo cinturón (`?user_id=` solo admin/instructor) |
| GET | `/at-risk/?days=30` | Admin/Instructor | Alumnos en riesgo de deserción |
| GET | `/exam-eligible/` | Admin/Instructor | Habilitados para rendir examen |
| GET | `/event-categories/` | Autenticado | Categorías activas; POST admin/instructor |
| GET/PUT/PATCH/DELETE | `/event-categories/{id}/` | GET autenticado; PUT/PATCH admin/instructor; DELETE admin | Detalle categoría |
| GET/POST | `/events/` | Autenticado; POST admin/instructor | Estudiantes solo ven verificados |
| GET/PUT/PATCH/DELETE | `/events/{id}/` | Ídem anterior | Detalle evento |
| POST | `/events/{id}/verify/` | Admin | Verifica evento |
| GET | `/events/verified/` | Autenticado | Solo verificados |
| GET/POST | `/participations/` | Autenticado (POST requiere evento verificado) | Estudiantes ven solo las propias |
| GET/PUT/PATCH/DELETE | `/participations/{id}/` | Dueño o admin/instructor | Detalle participación |
| POST | `/participations/{id}/verify/` | Admin | Verifica participación |
| GET | `/my-participations/` | Autenticado | Participaciones propias |

## Contratos exactos de los endpoints de retención

### `GET /api/performance/my-progress/`

```json
{
  "current_belt": {"id": 3, "name": "Verde", "order_number": 5} | null,
  "next_belt":    {"id": 4, "name": "Violeta"} | null,
  "classes_at_rank": 12,
  "required_classes": 20,
  "eligibility_percent": 60.0,
  "eligible_for_exam": false
}
```

Semántica documentada de `classes_at_rank`: como `UserProfile.belt_rank` no registra fecha de asignación, se usa como proxy la fecha del **último examen aprobado** (`ExamResult` con `graded=True and passed=True`, misma condición que promueve el cinturón): se cuentan asistencias reales con fecha de clase ≥ esa fecha. Si nunca aprobó un examen (o no tiene cinturón) → conteo all-time. El requisito aplicable es el del **cinturón actual** (o el primer cinturón activo si no tiene); si es `None` o ≤ 0 cae al default 20. `eligibility_percent` = min(100, redondeo a 1 decimal); `eligible_for_exam` usa comparación entera exacta (sin falsos positivos de redondeo).

### `GET /api/performance/at-risk/?days=30`

```json
{
  "count": 2,
  "results": [
    {"user_id": 7, "name": "Ana López", "email": "...", 
     "belt_name": "Amarillo" | null,
     "last_attendance_date": "2026-07-02T19:00:00-03:00" | null}
  ]
}
```

Estudiantes activos cuya última asistencia real fue hace más de `days` días (default 30), o quienes nunca asistieron y se registraron hace más de 30 días (`date_joined`). Orden ascendente por última asistencia; quienes nunca asistieron van primero.

### `GET /api/performance/exam-eligible/`

```json
{
  "count": 1,
  "results": [
    {"user_id": 7, "name": "Ana López", "email": "...",
     "current_belt": "Verde" | null,
     "next_belt": "Violeta",
     "classes_at_rank": 23,
     "required_classes": 20}
  ]
}
```

Reutiliza exactamente `_get_belt_progress()` (mismo criterio que `my-progress`).

### Derivación de `skill_level` (`GET /user-stats/`)

A partir de la categoría y orden del cinturón actual:

| Condición | Nivel |
|-----------|-------|
| Sin cinturón o error | `Principiante` |
| Categoría `Kyu A` | `Principiante` |
| Categoría `Kyu B` | `Intermedio` |
| `Dan`, offset 0 (primer Dan) | `Avanzado` |
| `Dan`, offset 1 | `Experto` |
| `Dan`, offset 2 | `Maestro` |
| `Dan`, offset ≥ 3 | `Gran Maestro` |

El offset se calcula contra el `order_number` del primer Dan activo. La tasa de asistencia del mismo endpoint compara asistencias reales contra clases pasadas no canceladas donde hubo reserva activa o registro de asistencia.

## Reglas de negocio

### Exámenes

- **Elegibilidad** (`ExamResult.can_take_exam`): cada usuario solo rinde para su **siguiente** cinturón activo por `order_number`; sin cinturón, solo el primero. Los lookups por nombre quedaron obsoletos tras migrar a FK — hoy compara IDs.
- **Creación de sesión** (`ExamSessionSerializer.create`): valida todos los participantes *antes* de crear (error agrupado con `invalid_participants`); crea la sesión, un `ExamResult` inicial no calificado por participante y notifica a cada uno.
- **Calificación** (`ExamResultSerializer`): llega con `parameter_scores[{parameter, score}]`; `passed = todas las notas >= 7`; `graded=True`. En update reemplaza el set completo de puntajes.
- **Promoción automática**: al pasar de no aprobado a aprobado (en `save()` del modelo o `update()` del serializer), se asigna al perfil el cinturón de la sesión y se notifica al alumno con cinturón anterior → nuevo.

### Eventos y participaciones

- Flujo verificación: cualquier autenticado ve eventos verificados; admin/instructor gestionan; solo admin verifica evento/participación.
- Un estudiante solo puede registrar participación en un evento **verificado** (validación con `ValidationError` en `perform_create`, porque DRF ignora retornos).
- `unique_together (event, user, event_category)` impide duplicar categoría en el mismo evento.

## Señales y tareas

| Disparador | Efecto |
|-----------|--------|
| Guardado/borrado de `ExamResult` | Refresca `PerformanceStatistics` del participante |
| Guardado/borrado de `EventParticipation` | Refresca `PerformanceStatistics` del usuario |

No hay tareas Celery propias; el módulo es reactivo a eventos CRUD.

## Puntos de atención

- `MyEventParticipationsView` conserva sentencias `print` de depuración que recorren **todas** las participaciones de la BD en cada request (ruido en logs y costo O(N)); funcionalmente correcto pero debe limpiarse antes de producción.
- `update_user_belt()` asigna el cinturón de la sesión sin verificar que sea consecutivo: la garantía de progresión depende de la validación de participantes en la creación de la sesión; una sesión creada por admin con participantes inválidos vía shell/admin Django saltaría pasos.
- `required_classes` es nullable por diseño (permite "sin requisito"), pero el cálculo lo trata como "usar 20"; documentar en la defensa que `NULL` ≡ 20 efectivos.
- `belt_level` (texto) sobrevive por compatibilidad con datos antiguos; el campo canónico es `belt_rank`.
- La lista de elegibles hace el cálculo por alumno en Python (correcto, deliberadamente simple); con miles de estudiantes convendría una versión agregada.
