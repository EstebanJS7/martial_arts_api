# 🐳 Docker Setup - Guía Rápida

## Inicio Rápido

```bash
cd martial_arts_api
docker-compose up --build
```

¡Eso es todo! El sistema levantará automáticamente:
- ✅ PostgreSQL (base de datos)
- ✅ Redis (Channels y Celery)
- ✅ Django (servidor web)
- ✅ Celery Worker (tareas asíncronas)
- ✅ Celery Beat (tareas programadas)

## Primera Vez

### 1. Crear superusuario
```bash
docker-compose exec web python manage.py createsuperuser
```

### 2. Acceder
- API: http://localhost:8000
- Admin: http://localhost:8000/admin

## Comandos Útiles

```bash
# Ver logs
docker-compose logs -f

# Detener todo
docker-compose down

# Reiniciar un servicio
docker-compose restart web

# Ejecutar comandos Django
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py shell
```

## Ver Documentación Completa

Ver `DOCKER_SETUP.md` para documentación detallada.


