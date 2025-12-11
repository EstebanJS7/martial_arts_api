#!/bin/bash
set -e

# Detectar si estamos en producción (usando Supabase/Upstash) o desarrollo (docker-compose)
# En producción, las URLs contienen "supabase" o "upstash", o no hay servicios locales "db" y "redis"
if [ -n "$DATABASE_URL" ] && ([[ "$DATABASE_URL" == *"supabase"* ]] || [[ "$DATABASE_URL" == *"railway"* ]] || [[ "$DATABASE_URL" == *"render"* ]]) || \
   [ -n "$REDIS_URL" ] && ([[ "$REDIS_URL" == *"upstash"* ]] || [[ "$REDIS_URL" == *"railway"* ]] || [[ "$REDIS_URL" == *"render"* ]]); then
  echo "Modo PRODUCCIÓN detectado (Supabase/Upstash/Railway/Render)"
  # En producción, no esperamos por db/redis locales
  # Solo verificamos que las variables estén configuradas
  if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL no está configurada"
    exit 1
  fi
  if [ -z "$REDIS_URL" ]; then
    echo "WARNING: REDIS_URL no está configurada (puede ser opcional)"
  fi
  echo "Variables de entorno configuradas correctamente"
elif ! nc -z db 5432 2>/dev/null; then
  # Si no podemos conectar a "db", asumimos producción
  echo "Modo PRODUCCIÓN detectado (no hay servicios locales)"
  if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL no está configurada"
    exit 1
  fi
  if [ -z "$REDIS_URL" ]; then
    echo "WARNING: REDIS_URL no está configurada (puede ser opcional)"
  fi
  echo "Variables de entorno configuradas correctamente"
else
  echo "Modo DESARROLLO detectado (docker-compose)"
  echo "Esperando a que PostgreSQL esté listo..."
  while ! nc -z db 5432 2>/dev/null; do
    sleep 0.1
  done
  echo "PostgreSQL está listo"

  echo "Esperando a que Redis esté listo..."
  while ! nc -z redis 6379 2>/dev/null; do
    sleep 0.1
  done
  echo "Redis está listo"
fi

echo "Preparando directorios de static y media..."
mkdir -p /app/staticfiles /app/media

if [ "${SKIP_MIGRATIONS}" != "true" ]; then
  echo "Ejecutando migraciones..."
  python manage.py migrate --noinput
else
  echo "Omitiendo migraciones (SKIP_MIGRATIONS=true)"
fi

if [ "${SKIP_COLLECTSTATIC}" != "true" ]; then
  echo "Recopilando archivos estáticos..."
  python manage.py collectstatic --noinput || true
else
  echo "Omitiendo collectstatic (SKIP_COLLECTSTATIC=true)"
fi

# Crear superusuario automáticamente si no existe (solo en producción)
if [ -n "$DATABASE_URL" ] && ([[ "$DATABASE_URL" == *"supabase"* ]] || [[ "$DATABASE_URL" == *"railway"* ]] || [[ "$DATABASE_URL" == *"render"* ]]); then
  echo "Verificando si existe un superusuario..."
  # Verificar si existe algún superusuario
  if ! python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print('EXISTS' if User.objects.filter(is_superuser=True).exists() else 'NOT_EXISTS')" 2>/dev/null | grep -q "EXISTS"; then
    echo "No se encontró ningún superusuario."
    # Verificar si se proporcionaron las variables de entorno necesarias
    if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
      echo "Creando superusuario con email: $DJANGO_SUPERUSER_EMAIL"
      # Intentar crear con createsuperuser primero
      export DJANGO_SUPERUSER_EMAIL DJANGO_SUPERUSER_PASSWORD
      python manage.py createsuperuser --noinput --email "$DJANGO_SUPERUSER_EMAIL" 2>/dev/null || {
        # Si falla, crear directamente con el shell (más robusto)
        python manage.py shell << PYEOF
import os
from django.contrib.auth import get_user_model
User = get_user_model()
email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
if email and password:
    if not User.objects.filter(email=email).exists():
        User.objects.create_superuser(email=email, password=password)
        print('Superusuario creado exitosamente')
    else:
        # Si existe, actualizar la contraseña
        user = User.objects.get(email=email)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print('Superusuario actualizado')
else:
    print('Variables de entorno no configuradas')
PYEOF
      }
      echo "✓ Superusuario creado o verificado"
    else
      echo "⚠️  ADVERTENCIA: No se creó superusuario automáticamente."
      echo "   Para crear uno automáticamente, configura las variables de entorno:"
      echo "   - DJANGO_SUPERUSER_EMAIL"
      echo "   - DJANGO_SUPERUSER_PASSWORD"
      echo "   O crea uno manualmente con: python manage.py createsuperuser"
    fi
  else
    echo "✓ Ya existe un superusuario en la base de datos"
  fi
fi

echo "Iniciando servidor..."
echo "[DEBUG] Verificando que el middleware esté disponible..."
python -c "from martial_arts_api.middleware import HealthCheckMiddleware; print('✓ HealthCheckMiddleware disponible')" || echo "✗ ERROR: HealthCheckMiddleware no disponible"

# Expandir $PORT en los argumentos (Railway pasa $PORT como literal)
# Railway inyecta $PORT como variable de entorno, pero cuando se pasa como argumento
# al script, viene como literal "$PORT", así que lo expandimos aquí
if [ -n "$PORT" ]; then
    expanded_args=()
    for arg in "$@"; do
        # Reemplazar $PORT con el valor real
        case "$arg" in
            *\$PORT*)
                arg=$(echo "$arg" | sed "s/\$PORT/$PORT/g")
                ;;
        esac
        expanded_args+=("$arg")
    done
    set -- "${expanded_args[@]}"
fi

exec "$@"



