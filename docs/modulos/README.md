# Documentación técnica por módulo — Martial Arts API (Django 5.1)

Documentación de referencia del backend, generada a partir de la lectura directa del código fuente. Describe **lo que el sistema hace hoy**, incluyendo la automatización de listas de espera, el ciclo de vida de pagos con recibos PDF, los endpoints de progreso de cinturones y el endurecimiento de seguridad.

## Índice

| Documento | Contenido |
|-----------|-----------|
| [00-arquitectura-general.md](00-arquitectura-general.md) | Stack, estructura del proyecto, flujo JWT con rotación/blacklist, roles y permisos, throttling, settings destacados, cadencia de Celery Beat, topología de despliegue y variables de entorno |
| [01-usuarios.md](01-usuarios.md) | `CustomUser`/`UserProfile`/roles, registro y login con anti-fuerza bruta, ciclo de contraseñas, auto-edición de perfil con campos protegidos, listado seguro de estudiantes |
| [02-clases.md](02-clases.md) | Clases, reservas concurrentes, asistencia manual y QR check-in, listas de espera automatizadas (posiciones compactadas + expiración), clases recurrentes, exportaciones PDF/Excel |
| [03-pagos.md](03-pagos.md) | Flujo manual sin gateway, generación idempotente de cuotas, vencidos y recordatorios, libro mayor `PaymentTransaction`, recibos secuenciales RC-YYYY-NNNNNN y PDF, exenciones |
| [04-performance.md](04-performance.md) | Cinturones con requisitos configurables, exámenes con promoción automática, eventos verificados, contratos JSON exactos de `my-progress` / `at-risk` / `exam-eligible`, derivación de skill level |
| [05-blog.md](05-blog.md) | Posts con categorías/tags slug automáticos, comentarios y ratings únicos 1–5, estado real de permisos de escritura |
| [06-galeria.md](06-galeria.md) | Galerías e ítems image/video con validación por tipo, Cloudinary opcional vs almacenamiento local dev-only |
| [07-recursos.md](07-recursos.md) | Biblioteca didáctica con enums tipo/categoría/nivel, tracking de vistas/descargas, descargas autenticadas; bugs detectados documentados |
| [08-notificaciones.md](08-notificaciones.md) | Modelo de notificaciones, WebSocket `/ws/notifications/` con JWT (tradeoff query param), preferencias, planificador de recordatorios y caveat de duplicados |
| [09-contacto.md](09-contacto.md) | Formulario público con correos síncronos y catálogo de academias |

## Convención de cada documento

`Propósito → Modelos y relaciones → Endpoints (tabla método/ruta/permisos/descripción) → Reglas de negocio → Señales y tareas → Puntos de atención`.

La sección final de cada módulo lista honestamente limitaciones, bugs conocidos y decisiones discutibles detectadas durante el relevamiento — útil para la defensa de tesis y para planificar trabajo futuro.
