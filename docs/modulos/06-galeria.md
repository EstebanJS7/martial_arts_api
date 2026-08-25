# 06 — Galería (`gallery`)

## Propósito

Galerías multimedia públicas de la academia (fotos y videos de actividades), con carga administrativa y lectura abierta para la landing.

## Modelos y relaciones

| Modelo | Campos / reglas |
|--------|-----------------|
| `Gallery` | `title`, `description`, `cover_image` (`gallery/covers/`); orden por creación descendente |
| `GalleryItem` | FK obligatoria a `Gallery` (`CASCADE`); `media_type`: `image` \| `video` (default `image`); campos `image` (`gallery/images/`) y `video` (`gallery/videos/`) mutuamente según tipo; `description`; `uploaded_at` |

Relación de navegación: `GallerySerializer` anida todos los ítems de la galería vía la relación inversa `galleryitem_set` (ordenados por fecha de subida).

## Endpoints

Prefijo global: `/api/gallery/`.

| Método | Ruta | Permisos | Descripción |
|--------|------|----------|-------------|
| GET/POST | `/galleries/` | GET AllowAny (sin throttle) / POST Admin-Instructor | Listado paginado (12/página) con caché; crea galería |
| GET/PUT/PATCH/DELETE | `/galleries/{id}/` | GET AllowAny / resto Admin-Instructor | Detalle con ítems prefetchados |
| GET/POST | `/items/` | GET AllowAny / POST Admin-Instructor | Ítems sueltos |
| GET/PUT/PATCH/DELETE | `/items/{id}/` | GET AllowAny / resto Admin-Instructor | Gestión de ítem |

## Reglas de negocio

### Validación media_type ↔ archivo (serializer)

```python
media_type == 'image' → exige data['image'] presente
media_type == 'video' → exige data['video'] presente
```

El incumplimiento devuelve 400 con mensaje explícito. No se valida el caso inverso (subir ambos archivos a la vez no está prohibido, pero el serializer solo garantiza el requerido para el tipo declarado).

### Almacenamiento

- **Con Cloudinary**: si las tres variables `CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET` están presentes en el entorno, `STORAGES['default']` es `MediaCloudinaryStorage` y las imágenes/videos suben a Cloudinary; `MEDIA_URL` apunta al dominio CDN. Aplica a toda la app (perfil, blog, galería, recursos).
- **Sin Cloudinary**: `FileSystemStorage` sobre `MEDIA_ROOT/media/`. En producción esto solo funciona si algo sirve `/media/` — por diseño el modo local es **solo desarrollo** (Render/Daphne no sirve media en prod sin Cloudinary).
- Las URLs devueltas por los serializers son absolutas (`request.build_absolute_uri` cuando corresponde) o directas del storage.

## Señales y tareas

Ninguna. Módulo CRUD puro.

## Puntos de atención

- La lectura pública sin throttling incluye el listado completo de ítems anidados por galería: con volúmenes grandes convendría paginar ítems dentro del detalle.
- El default `media_type='image'` combinado con la validación evita ítems vacíos, pero permite cambiar el tipo en un PATCH sin revalidar el archivo contrario (DRF valida contra el payload completo solo si se envían los campos).
- Sin credenciales de Cloudinary en producción, cualquier imagen cargada se perderá al reiniciar el contenedor (disco efímero): operar producción siempre con Cloudinary configurado.
