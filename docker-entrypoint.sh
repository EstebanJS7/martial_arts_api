#!/bin/bash
set -e

# Detectar si estamos en producción (usando Supabase/Upstash) o desarrollo (docker-compose)
if [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" == *"supabase"* ]] || [ -n "$REDIS_URL" ] && [[ "$REDIS_URL" == *"upstash"* ]]; then
  echo "Modo PRODUCCIÓN detectado (Supabase/Upstash)"
  # En producción, no esperamos por db/redis locales
  # Solo verificamos que las variables estén configuradas
  if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL no está configurada"
    exit 1
  fi
  if [ -z "$REDIS_URL" ]; then
    echo "ERROR: REDIS_URL no está configurada"
    exit 1
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

echo "Iniciando servidor..."
exec "$@"



