# 05 — Blog (`blog`)

## Propósito

Contenido editorial de la comunidad: publicaciones con imagen, categoría y tags; comentarios y calificaciones (ratings) por parte de usuarios registrados; entradas destacadas y estadísticas por post para la landing.

## Modelos y relaciones

| Modelo | Campos / reglas |
|--------|-----------------|
| `Category` | `name` único, `slug` único autogenerado con `slugify(name)` en `save()`, `color` hex (default `#3B82F6`) |
| `Tag` | Igual patrón slug automático; color default `#6B7280` |
| `BlogPost` | `title`, `content`, `author` FK usuario (CASCADE), `category` FK SET_NULL nullable, M2M `tags`, `image` (`blog_images/`), `is_featured` |
| `Comment` | FK post (related `comments`) + `user`; texto libre |
| `Rating` | FK post + user, **unique_together `(blog_post, user)`**, `score` 1–5 validado con `MinValue/MaxValueValidator` |

## Endpoints

Prefijo global: `/api/blog/`.

| Método | Ruta | Permisos | Descripción |
|--------|------|----------|-------------|
| GET/POST | `/posts/` | Lectura pública / escritura autenticada | Listado paginado con caché (`CACHE_TTL`); sin throttle en GET |
| GET/PUT/PATCH/DELETE | `/posts/{id}/` | Autor o staff (`IsAuthorOrAdmin`) | Detalle con caché en retrieve |
| GET | `/posts/{id}/stats/` | AllowAny | Totales de ratings/comments, promedio y distribución 1–5 estrellas |
| GET/POST | `/posts/{id}/comments/` | Lectura pública / escritura autenticada | Comentarios del post |
| GET/PUT/PATCH/DELETE | `/comments/{id}/` | Autenticado (queryset acotado a propios) | Edición/borrado del propio comentario |
| POST | `/posts/{id}/rate/` | Autenticado | Upsert del rating propio del post |
| GET/PUT/PATCH/DELETE | `/ratings/{id}/` | Autenticado (propios) | Gestión del rating propio |
| GET | `/posts/{id}/ratings/` | AllowAny | Todos los ratings del post |
| GET | `/featured/` | AllowAny | Hasta 3 destacadas; completa con recientes si faltan |
| GET/POST | `/categories/` | Lectura pública / escritura autenticada | Con `posts_count` calculado |
| GET/PUT/PATCH/DELETE | `/categories/{id}/` | Ídem anterior | CRUD categoría |
| GET/POST | `/tags/` · GET/PUT/PATCH/DELETE `/tags/{id}/` | Ídem anterior | CRUD tags |
| GET | `/categories/{id}/posts/` · `/tags/{id}/posts/` | AllowAny | Posts filtrados con paginación manual (`page`, `page_size`) |

## Reglas de negocio

- **Slugs automáticos**: tanto `Category` como `Tag` generan su slug en `save()` solo si está vacío; el serializer lo expone read-only. La unicidad la garantiza la BD.
- **Ratings upsert**: `POST /posts/{id}/rate/` busca el rating previo del usuario para ese post: si existe actualiza `score`, si no crea. La unicidad `(post, user)` respalda la operación a nivel BD.
- **Escritura por ID**: el serializer acepta `category_id` y `tag_ids` write-only; en create ignora silenciosamente IDs inexistentes, en update limpia la relación si llega lista vacía o `null`.
- **Caché**: listado y detalle de posts usan `cache_page(settings.CACHE_TTL)` (15 min). Tras publicar/editar puede haber hasta 15 min de contenido viejo en lecturas públicas — comportamiento esperado, no bug.
- **Autoría**: `perform_create` asigna `author = request.user`. El guard de edición es `IsAuthorOrAdmin`, que autoriza a `is_staff` (superusuarios/staff de Django), no al rol `admin` del perfil.

## Señales y tareas

El módulo no define señales ni tareas Celery. Es puramente CRUD + agregaciones on-demand (`stats` calcula en cada request).

## Puntos de atención (estado real de permisos de escritura)

- **Cualquier usuario registrado puede crear posts** (`IsAuthenticatedOrReadOnly` en `BlogPostListView`): no hay restricción a instructor/admin. Igual para **categorías y tags** (`CategoryListView`/`TagListView`). Es el estado actual del código; si la intención era solo-staff, hay que endurecer permisos.
- `CommentDetailView.perform_update/perform_destroy` contienen guards que devuelven `Response(...)` dentro de métodos cuyo retorno DRF ignora: son código muerto. No es explotable porque el queryset ya filtra por `user=self.request.user`, pero conviene eliminarlos o convertirlos en excepciones.
- `average_rating` y conteos se calculan por instancia (N+1 potencial en listados grandes); aceptable para el volumen actual del proyecto.
- Los slugs no se regeneran si se renombra una categoría/tag (solo se setean cuando están vacíos): renombrar conserva el slug viejo.
