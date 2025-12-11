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
  echo "=========================================="
  echo "Verificando creación de superusuario..."
  echo "=========================================="
  
  # Verificar que la base de datos esté lista (las migraciones se ejecutaron)
  echo "Verificando conexión a la base de datos..."
  if ! python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('OK')" 2>/dev/null | grep -q "OK"; then
    echo "⚠️  ADVERTENCIA: No se pudo conectar a la base de datos. Omitiendo creación de superusuario."
    echo "   Asegúrate de que las migraciones se ejecutaron correctamente."
  else
    echo "✓ Conexión a la base de datos verificada"
    
    # Verificar si se proporcionaron las variables de entorno
    if [ -z "$DJANGO_SUPERUSER_EMAIL" ] || [ -z "$DJANGO_SUPERUSER_PASSWORD" ]; then
      echo "⚠️  ADVERTENCIA: Variables de entorno para superusuario no configuradas."
      echo "   DJANGO_SUPERUSER_EMAIL: ${DJANGO_SUPERUSER_EMAIL:-NO CONFIGURADA}"
      echo "   DJANGO_SUPERUSER_PASSWORD: ${DJANGO_SUPERUSER_PASSWORD:+CONFIGURADA (oculta)} ${DJANGO_SUPERUSER_PASSWORD:-NO CONFIGURADA}"
      echo "   Para crear uno automáticamente, configura estas variables en Railway."
    else
      echo "✓ Variables de entorno encontradas:"
      echo "   Email: $DJANGO_SUPERUSER_EMAIL"
      echo "   Password: [OCULTA]"
      
      # Crear superusuario directamente con shell de Python (más confiable)
      echo "Creando/verificando superusuario..."
      python manage.py shell << PYEOF
import os
import sys
from django.contrib.auth import get_user_model

try:
    User = get_user_model()
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '').strip()
    
    if not email or not password:
        print('ERROR: Email o contraseña vacíos')
        sys.exit(1)
    
    # Normalizar email
    email = User.objects.normalize_email(email)
    
    # Verificar si el usuario ya existe
    if User.objects.filter(email=email).exists():
        user = User.objects.get(email=email)
        # Actualizar para asegurar que sea superusuario
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        print(f'✓ Superusuario existente actualizado: {email}')
    else:
        # Crear nuevo superusuario
        User.objects.create_superuser(email=email, password=password)
        print(f'✓ Superusuario creado exitosamente: {email}')
    
    # Verificar que se creó correctamente
    user = User.objects.get(email=email)
    if user.is_superuser and user.is_staff:
        print(f'✓ Verificación: Superusuario {email} está activo y tiene permisos de administrador')
    else:
        print(f'⚠️  ADVERTENCIA: El usuario {email} existe pero no tiene permisos completos')
        sys.exit(1)
        
except Exception as e:
    print(f'ERROR al crear superusuario: {str(e)}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF
      
      if [ $? -eq 0 ]; then
        echo "✓ Proceso de creación de superusuario completado"
      else
        echo "✗ ERROR: Falló la creación del superusuario. Revisa los logs arriba."
      fi
    fi
  fi
  echo "=========================================="
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



