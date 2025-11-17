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

echo "Ejecutando migraciones..."
python manage.py migrate --noinput

echo "Recopilando archivos estáticos..."
python manage.py collectstatic --noinput || true

echo "Iniciando servidor..."
exec "$@"


