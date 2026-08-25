# 07 — Recursos (`resources`)

## Propósito

Biblioteca didáctica: videos, documentos, enlaces, imágenes y audio categorizados por técnica/nivel, con etiquetas, destacados, contadores de vistas/descargas y estadísticas para instructores.

## Modelos y relaciones

### Enums (`TextChoices`)

| Enum | Valores |
|------|---------|
| `ResourceType` | `VIDEO`, `DOCUMENT`, `LINK`, `IMAGE`, `AUDIO` |
| `ResourceCategory` | `TECHNIQUE`, `THEORY`, `HISTORY`, `PHILOSOPHY`, `TRAINING`, `COMPETITION`, `OTHER` |
| `ResourceLevel` | `KYU_A`, `KYU_B`, `DAN`, `ALL` |

### Modelos

| Modelo | Campos / reglas |
|--------|-----------------|
| `Resource` | `title`; `type/category/level` con defaults; contenido: `url` externa **o** `file` (`resources/`) + `thumbnail` + `file_size` + `duration` (segundos); `author` FK nullable; M2M `tags` → `ResourceTag`; contadores `views_count`/`downloads_count`; flags `is_featured`, `is_premium`. Métodos `increment_views()` / `increment_downloads()` (update dirigido) |
| `ResourceTag` | Etiqueta simple con `name` único |

## Endpoints

Prefijo global: `/api/resources/`.

| Método | Ruta | Permisos | Descripción |
|--------|------|----------|-------------|
| GET | `/` | Autenticado* | Listado paginado; filtros `type/category/level/is_featured`, búsqueda `?search=`, orden `?ordering=`; filtro múltiple `?tags=id1&id2` |
| POST | `/create/` | Admin/Instructor | Alta multipart (`MultiPartParser`) con archivo/thumbnail |
| GET | `/{id}/` | Autenticado* | Detalle completo; **incrementa `views_count`** en cada GET |
| PUT/PATCH/DELETE | `/{id}/` | Admin/Instructor o autor del recurso (`check_object_permissions`) | Edición/borrado |
| GET | `/featured/` | Autenticado* | Destacados con caché de 15 min |
| GET/POST | `/tags/` | GET autenticado / POST admin-instructor | Etiquetas de recursos |
| GET | `/{id}/download/` | Autenticado | Devuelve URL absoluta del archivo + filename + size e incrementa contador de descargas |
| POST | `/{id}/view/` | Autenticado | Registra vista explícita (complementa el incremento automático del detalle) |
| GET | `/stats/` | Admin/Instructor | Estadísticas agregadas — **actualmente roto**, ver Puntos de atención |

\* El listado/detalle usan `IsAuthenticatedOrReadOnly`: técnicamente accesibles sin token, aunque el flujo normal del frontend los consume autenticado.

## Reglas de negocio

- **Tracking**: dos vías de conteo de vistas (GET de detalle y `POST /{id}/view/`) — pueden sumar doble si el frontend usa ambas. Descargas cuentan al solicitar la URL, no al transferir bytes.
- **Descargas autenticadas**: el endpoint requiere JWT y devuelve `download_url` absoluta (archivo en storage o URL externa). No sirve el binario él mismo: quien descarga accede después a la URL del storage. Con Cloudinary es un CDN público; en desarrollo local Django sirve `/media/`.
- **Autorización de objeto**: la edición permite además del rol admin/instructor al `author` del recurso.
- Serializadores separados: lista (sin archivo), detalle (con `file_url`, tags) y creación/edición (multipart con `tags` como IDs).

## Señales y tareas

Ninguna.

## Puntos de atención

1. **Bug confirmado por inspección — `GET /api/resources/stats/` falla**: `resource_stats_view` usa `models.Sum(...)` pero el módulo solo importa `Q, Sum` de `django.db.models` (nunca importa el módulo `models`). Cualquier invocación lanza `NameError` → 500. Corrección trivial: usar `Sum` ya importado. Documentado tal cual está hoy el código.
2. **Sospecha fuerte — serializador con campo inexistente**: `ResourceAuthorSerializer` declara `username` en `fields`, pero `CustomUser` eliminó ese campo (`username = None`). DRF construye campos perezosamente: el primer intento de serializar un recurso (listado/detalle) debería levantar `ImproperlyConfigured: Field name 'username' is not valid for model 'User'` → 500. Verificar en runtime; la corrección es quitar `username` de fields y de `get_name()`.
3. Los contadores no son idempotentes ni deduplicados (refrescar la página cuenta otra vista).
4. `file_size` es opcional y no se calcula automáticamente al subir el archivo: puede quedar `null` aunque haya archivo.
