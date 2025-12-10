#!/bin/bash
set -e

echo "Esperando a que PostgreSQL esté listo..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "PostgreSQL está listo"

echo "Esperando a que Redis esté listo..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "Redis está listo"

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



