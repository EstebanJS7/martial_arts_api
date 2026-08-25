# 03 — Pagos (`payments`)

## Propósito

Administración de cuotas mensuales con **flujo 100% manual, sin pasarela de pago**: generación automática de cuotas (señal + Celery), registro de cobros en efectivo/transferencia por parte de admin/instructores, libro mayor de transacciones con recibos secuenciales en PDF, marcación de vencidos y dashboards de recaudación.

## Modelos y relaciones

| Modelo | Campos / reglas clave |
|--------|----------------------|
| `QuotaConfig` | `amount`, `due_day` (día de vencimiento mensual, default 10), `is_active`. `save()` **desactiva** cualquier otra config activa → existe a lo sumo una activa. `get_active_config()` la devuelve |
| `Payment` | `user` FK; `amount`, `amount_paid` (default 0); `due_date`; `period` (`YYYY-MM`) para idempotencia; flags `is_paid`, `is_fully_paid`, `is_overdue`. `save()` completa `due_date`/`amount` desde la config activa si faltan, deriva `period` de `due_date`, y si `is_fully_paid` fuerza `amount_paid = amount` e `is_paid = True` |
| `PaymentTransaction` | Libro mayor: FK `payment` (related `transactions`), `amount`, `payment_method` (**solo `cash` \| `transfer`**), `reference_number` (voucher), `registered_by` FK usuario que registró, `external_transaction_id`, `receipt_number` único formato **RC-YYYY-NNNNNN** |
| `PaymentStats` | Snapshot diario/mensual de recaudación (`date` única) usado por reportes históricos |

Índices destacados: `(user, period)` soporta la idempotencia mensual; `(user, due_date)` y `(due_date, is_fully_paid)` las consultas de morosidad.

## Endpoints

Prefijo global: `/api/payments/`.

| Método | Ruta | Permisos | Descripción |
|--------|------|----------|-------------|
| POST | `/apply-payment/{user_id}/{monto}/` | Admin/Instructor (throttle sensitive 20/h) | Aplica un monto en cascada sobre pagos pendientes (FIFO por vencimiento); acepta `payment_method`, `reference_number`, `description`. Devuelve `excess_amount` si sobra |
| GET | `/list/` | Admin (DRF `IsAdminUser`) | Todos los pagos, paginados, filtrables (`PaymentFilter`: email icontains, rangos `date_payment`/`due_date`) |
| GET/PUT/PATCH/DELETE | `/detail/{id}/` | Admin | CRUD; PATCH que cambia `amount` registra transacción de ajuste con delta y recibo |
| POST | `/create/` | Admin/Instructor | Crea pago; opcionalmente crea su primera transacción (método/ref) y luego auto-crea la cuota del mes siguiente |
| GET/POST | `/quota-config/` | Admin | Lista/crea configuraciones de cuota |
| GET/PUT/PATCH/DELETE | `/quota-config/{id}/` | Admin | Detalle de configuración |
| GET | `/check-due-status/{user_id}/` | Autenticado (solo propio; admin ve cualquiera) | `{status: overdue\|up_to_date, ...}` con IDs vencidos o próxima fecha |
| GET | `/my-payments/` | Autenticado | Pagos propios paginados con transacciones anidadas |
| GET | `/{id}/transactions/` | Dueño, admin o instructor | Transacciones del pago |
| **GET** | **`/{id}/receipt.pdf`** | Dueño, admin o instructor | **Recibo PDF. Sin barra final** (ver Puntos de atención) |
| GET | `/dashboard/` | Admin/Instructor | Overview + tendencias + top pagadores + distribución por método |
| GET | `/stats/monthly/?year=&month=` | Admin/Instructor | Estadísticas de un mes |
| GET | `/stats/trends/?period=n` | Admin/Instructor | Tendencias mensuales |
| GET | `/report/?start_date=&end_date=` | Admin/Instructor (chequeo manual dentro de la vista) | Reporte general con estadísticas mensuales |

## Reglas de negocio

### Flujo manual sin gateway

El dinero nunca se mueve por la API: un instructor/admin registra físicamente el cobro (efectivo o transferencia) y luego lo **aplica** vía `apply-payment`. Cada aplicación genera una `PaymentTransaction` con auditoría completa (quién, método, referencia).

### Cascada de aplicación de pagos

`PaymentService.apply_payment(user, monto)` recorre los pagos no completamente pagados ordenados por `due_date` ascendente:

1. Si el monto cubre la deuda de la cuota → marca `is_paid`/`is_fully_paid`, crea transacción "Pago completado" y descuenta.
2. Si es menor → pago parcial: incrementa `amount_paid`, crea transacción "Pago parcial"; si con eso se iguala el monto, marca pagado.
3. El remanente (si el usuario pagó de más) se devuelve en la respuesta como `excess_amount`.

### Recibos secuenciales RC-YYYY-NNNNNN

`generate_next_receipt_number()` debe ejecutarse **dentro** del bloque atómico donde se crea la transacción: toma `select_for_update()` sobre los recibos del año actual, lee el máximo y suma 1 con padding de 6 dígitos (`RC-2026-000001`). Ante un recibo con formato inesperado cae a `count() + 1`. La unicidad final la garantiza además el `unique=True` del campo.

### Recibo PDF

`GET /api/payments/{id}/receipt.pdf` renderiza con ReportLab: encabezado placeholder de academia, número de recibo (o fallback `PAGO-{id}` si no hay transacciones con recibo), alumno, período, vencimiento, monto pagado de la última transacción, método traducido, referencia y quién registró. Respuesta `inline; filename="recibo_RC-....pdf"`.

### Exención (`is_exempt`)

Los estudiantes con `UserProfile.is_exempt=True` quedan fuera de la generación mensual (`generate_monthly_quotas`) y anual (`generate_annual_payments_for_all_students`). La exención solo puede asignarla un admin (campo read-only en el PATCH propio del perfil).

### Cuota activa única

Marcar una `QuotaConfig` con `is_active=True` desactiva automáticamente las demás (override de `save()`). Los flujos automáticos usan `get_active_config()`.

## Señales y tareas

### Señales

| Disparador | Efecto |
|-----------|--------|
| Creación de `Payment` | Notifica al alumno: nuevo pago con monto y vencimiento |
| Actualización de `Payment` a pagado | Notifica acreditación |
| Creación de `PaymentTransaction` | Notifica registro de transacción |

Nota: estas señales generan notificación incluso cuando el disparador fue la tarea programada de generación — el alumno recibe aviso de cada cuota creada.

### Tareas Celery

| Tarea | Cadencia (Beat) | Comportamiento |
|-------|------------------|----------------|
| `payments.tasks.generate_monthly_quotas` | Día 1, 06:05 | Crea la cuota del mes para estudiantes activos no exentos. **Idempotente**: `get_or_create(user, period='YYYY-MM')` |
| `payments.tasks.mark_overdue_payments` | Diaria, 06:45 | Marca `is_overdue=True` en vencidos no pagados y **limpia** la marca si se pagaron o la fecha aún no llegó |
| `payments.tasks.remind_upcoming_due_payments` | Diaria, 09:15 | Notifica cuotas que vencen exactamente en 3 días sin pagar |
| `payments.tasks.notify_overdue_payments` | Diaria, 09:00 | Notifica cada pago vencido con días de atraso |
| `payments.tasks.generate_monthly_report` | Días 28–31, 10:00 (auto-verifica último día) | Envía resumen del mes a admins por notificaciones |
| `martial_arts_api.tasks.generate_annual_payments_for_all_students` | 1 de enero, 00:00 | Cuotas de febrero–diciembre para estudiantes no exentos (proyecto raíz) |

## Puntos de atención

- **URL del recibo sin barra final**: la ruta se define como `<int:payment_id>/receipt.pdf`. Con `APPEND_SLASH=True`, pedir `/receipt.pdf/` no matchea y produce 404 tras intentar redirección. El frontend debe llamar exactamente `.../receipt.pdf`.
- **Recordatorios de vencidos duplicados**: `notify_overdue_payments` corre todos los días y notifica **cada** pago vencido; no existe campo `last_notified_date` (el propio código lo admite en comentario). El alumno recibe un recordatorio diario por cada deuda mientras persista.
- Inconsistencia menor entre helpers: `create_next_month_payment` (usada al crear un pago manual) toma `QuotaConfig.objects.latest('id')` en lugar de `get_active_config()`; si se crean configs nuevas inactivas después de la activa, ese flujo usaría el monto equivocado.
- El ciclo de vida completo depende de Celery Beat corriendo: sin beat no hay generación de cuotas ni marcación de vencidos (`is_overdue` quedaría congelada; el QR check-in usa igualmente `due_date` como resguardo).
- `PaymentDetailView.perform_update` emite recibo por cada ajuste de monto (delta ≠ 0), lo que consume números de la serie RC aunque no haya dinero involucrado: decisión válida para trazabilidad, pero infla la secuencia.
- `PaymentStats` se puebla solo vía `generate_monthly_stats` del servicio, que hoy no está cableada a Beat; los dashboards vivos calculan sobre `Payment` directamente.
