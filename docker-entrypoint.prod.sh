#!/bin/bash
set -e

echo "Preparando directorios de static y media..."
mkdir -p /app/staticfiles /app/media

# En producción, no esperamos por db/redis locales (usamos Supabase/Upstash)
# Solo verificamos que las variables de entorno estén configuradas
if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL no está configurada"
  exit 1
fi

if [ -z "$REDIS_URL" ]; then
  echo "ERROR: REDIS_URL no está configurada"
  exit 1
fi

echo "Variables de entorno configuradas correctamente"

if [ "${SKIP_MIGRATIONS}" != "true" ]; then
  echo "Ejecutando migraciones..."
  python manage.py migrate --noinput || echo "Advertencia: Migraciones fallaron, continuando..."
else
  echo "Omitiendo migraciones (SKIP_MIGRATIONS=true)"
fi

if [ "${SKIP_COLLECTSTATIC}" != "true" ]; then
  echo "Recopilando archivos estáticos..."
  python manage.py collectstatic --noinput || echo "Advertencia: collectstatic falló, continuando..."
else
  echo "Omitiendo collectstatic (SKIP_COLLECTSTATIC=true)"
fi

echo "Iniciando servidor..."
exec "$@"

