# Docker Setup - Backend Completo

Este proyecto incluye una configuración completa de Docker Compose para levantar todo el backend de una vez.

## 🚀 Inicio Rápido

### 1. Levantar todos los servicios
```bash
cd martial_arts_api
docker-compose up --build
```

### 2. Ejecutar migraciones (primera vez)
```bash
docker-compose exec web python manage.py migrate
```

### 3. Crear superusuario (opcional)
```bash
docker-compose exec web python manage.py createsuperuser
```

### 4. Acceder a la aplicación
- **API**: http://localhost:8000
- **Admin**: http://localhost:8000/admin
- **API Docs**: http://localhost:8000/api/docs

## 📦 Servicios Incluidos

El `docker-compose.yml` incluye:

1. **PostgreSQL** (`db`)
   - Base de datos principal
   - Puerto: 5432
   - Datos persistentes en volumen

2. **Redis** (`redis`)
   - Para Channels (WebSockets)
   - Para Celery (tareas asíncronas)
   - Puerto: 6379
   - Datos persistentes en volumen

3. **Django Web** (`web`)
   - Servidor ASGI con Daphne
   - Puerto: 8000
   - Hot-reload con volúmenes

4. **Celery Worker** (`celery_worker`)
   - Procesa tareas asíncronas
   - Notificaciones, pagos, etc.

5. **Celery Beat** (`celery_beat`)
   - Scheduler de tareas programadas
   - Recordatorios, reportes, etc.

## 🛠️ Comandos Útiles

### Levantar servicios
```bash
# Levantar en segundo plano
docker-compose up -d

# Levantar con logs
docker-compose up

# Reconstruir imágenes
docker-compose up --build
```

### Detener servicios
```bash
# Detener servicios
docker-compose down

# Detener y eliminar volúmenes (⚠️ elimina datos)
docker-compose down -v
```

### Ver logs
```bash
# Todos los servicios
docker-compose logs -f

# Servicio específico
docker-compose logs -f web
docker-compose logs -f celery_worker
docker-compose logs -f celery_beat
```

### Ejecutar comandos Django
```bash
# Migraciones
docker-compose exec web python manage.py migrate

# Crear superusuario
docker-compose exec web python manage.py createsuperuser

# Shell de Django
docker-compose exec web python manage.py shell

# Collectstatic
docker-compose exec web python manage.py collectstatic --noinput
```

### Ejecutar comandos de Celery
```bash
# Ver tareas activas
docker-compose exec celery_worker celery -A martial_arts_api inspect active

# Ver tareas programadas
docker-compose exec celery_beat celery -A martial_arts_api inspect scheduled
```

## 🔧 Configuración

### Variables de Entorno

Crea un archivo `.env` en `martial_arts_api/` (opcional):

```env
DEBUG=True
SECRET_KEY=tu-secret-key-aqui
DATABASE_URL=postgresql://martial_user:abc12345@db:5432/martial_arts_db
REDIS_URL=redis://redis:6379/1
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### Cambiar Credenciales de Base de Datos

Edita `docker-compose.yml`:
```yaml
db:
  environment:
    POSTGRES_DB: tu_db
    POSTGRES_USER: tu_usuario
    POSTGRES_PASSWORD: tu_password
```

Y actualiza `DATABASE_URL` en los servicios.

## 📁 Estructura de Volúmenes

- `postgres_data`: Datos de PostgreSQL
- `redis_data`: Datos de Redis
- `static_volume`: Archivos estáticos de Django
- `media_volume`: Archivos media subidos

## 🐛 Troubleshooting

### Error: "Port already in use"
```bash
# Ver qué proceso usa el puerto
# Windows:
netstat -ano | findstr :8000

# Linux/Mac:
lsof -i :8000

# O cambiar el puerto en docker-compose.yml
ports:
  - "8001:8000"  # Puerto externo:interno
```

### Error: "Connection refused" (Base de datos)
- Verifica que el servicio `db` esté saludable: `docker-compose ps`
- Espera a que PostgreSQL termine de inicializar (puede tardar unos segundos)

### Error: "Module not found"
```bash
# Reconstruir imagen
docker-compose build --no-cache web
docker-compose up -d
```

### Las migraciones no se aplican
```bash
# Ejecutar migraciones manualmente
docker-compose exec web python manage.py migrate
```

### Celery no procesa tareas
```bash
# Verificar que Redis esté funcionando
docker-compose exec redis redis-cli ping

# Verificar logs de Celery
docker-compose logs celery_worker
```

### Reiniciar un servicio específico
```bash
docker-compose restart web
docker-compose restart celery_worker
docker-compose restart celery_beat
```

## 🔄 Desarrollo

### Hot Reload

Los volúmenes están configurados para hot-reload:
- Cambios en código Python se reflejan automáticamente
- No necesitas reconstruir la imagen

### Agregar nuevas dependencias

1. Agregar a `requirements.txt`
2. Reconstruir: `docker-compose build web`
3. Reiniciar: `docker-compose restart web`

## 🚢 Producción

Para producción, considera:

1. **Variables de entorno seguras**: Usa `.env` o secrets management
2. **SSL/TLS**: Configura reverse proxy (nginx)
3. **Backups**: Configura backups automáticos de PostgreSQL
4. **Monitoreo**: Agrega healthchecks y logging
5. **Escalado**: Usa múltiples workers de Celery

### Ejemplo de configuración de producción

```yaml
celery_worker:
  deploy:
    replicas: 3  # Múltiples workers
```

## 📝 Notas

- Los datos se persisten en volúmenes Docker
- Para limpiar todo: `docker-compose down -v` (⚠️ elimina datos)
- Los logs se muestran en tiempo real con `docker-compose logs -f`


