#!/usr/bin/env python
"""
Script para verificar la configuración de despliegue
Ejecutar: python scripts/check_deployment.py
"""

import os
import sys
import django
from pathlib import Path

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'martial_arts_api.settings')
django.setup()

from django.conf import settings
from django.core.management.utils import get_random_secret_key


def check_secret_key():
    """Verifica que SECRET_KEY esté configurada y sea segura"""
    print("🔐 Verificando SECRET_KEY...")
    secret_key = settings.SECRET_KEY
    
    if 'insecure' in secret_key.lower() or secret_key == 'django-insecure-s@@ksa+i2$#!^a-5r6hbxl-wvzxefn!&o)m8j#@s%h@_-oiyi=':
        print("  ❌ SECRET_KEY es insegura (valor por defecto detectado)")
        print("  💡 Genera una nueva con: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\"")
        return False
    else:
        print("  ✅ SECRET_KEY configurada")
        return True


def check_debug():
    """Verifica que DEBUG esté en False en producción"""
    print("\n🐛 Verificando DEBUG...")
    if settings.DEBUG:
        print("  ⚠️  DEBUG está en True (no recomendado para producción)")
        print("  💡 Configura DEBUG=False en producción")
        return False
    else:
        print("  ✅ DEBUG está en False")
        return True


def check_allowed_hosts():
    """Verifica que ALLOWED_HOSTS esté configurado"""
    print("\n🌐 Verificando ALLOWED_HOSTS...")
    allowed_hosts = settings.ALLOWED_HOSTS
    
    if not allowed_hosts:
        print("  ❌ ALLOWED_HOSTS está vacío")
        print("  💡 Configura ALLOWED_HOSTS con tu dominio")
        return False
    elif 'localhost' in allowed_hosts and not settings.DEBUG:
        print("  ⚠️  ALLOWED_HOSTS incluye localhost (no recomendado para producción)")
        return False
    else:
        print(f"  ✅ ALLOWED_HOSTS configurado: {', '.join(allowed_hosts)}")
        return True


def check_database():
    """Verifica la conexión a la base de datos"""
    print("\n💾 Verificando Base de Datos...")
    try:
        from django.db import connection
        connection.ensure_connection()
        print("  ✅ Conexión a base de datos exitosa")
        return True
    except Exception as e:
        print(f"  ❌ Error conectando a la base de datos: {e}")
        print("  💡 Verifica DATABASE_URL o configuración de base de datos")
        return False


def check_redis():
    """Verifica la conexión a Redis"""
    print("\n🔴 Verificando Redis...")
    try:
        import redis
        redis_url = settings.REDIS_URL
        r = redis.from_url(redis_url)
        r.ping()
        print("  ✅ Conexión a Redis exitosa")
        return True
    except Exception as e:
        print(f"  ❌ Error conectando a Redis: {e}")
        print("  💡 Verifica REDIS_URL")
        return False


def check_cors():
    """Verifica la configuración de CORS"""
    print("\n🔗 Verificando CORS...")
    if settings.DEBUG and settings.CORS_ALLOW_ALL_ORIGINS:
        print("  ⚠️  CORS permite todos los orígenes (solo en desarrollo)")
    elif not settings.CORS_ALLOWED_ORIGINS:
        print("  ⚠️  CORS_ALLOWED_ORIGINS está vacío")
        print("  💡 Configura CORS_ALLOWED_ORIGINS con tu frontend")
        return False
    else:
        print(f"  ✅ CORS configurado: {', '.join(settings.CORS_ALLOWED_ORIGINS)}")
    return True


def check_static_files():
    """Verifica que los archivos estáticos estén configurados"""
    print("\n📁 Verificando Archivos Estáticos...")
    static_root = settings.STATIC_ROOT
    if not static_root or not os.path.exists(static_root):
        print(f"  ⚠️  STATIC_ROOT no existe: {static_root}")
        print("  💡 Ejecuta: python manage.py collectstatic")
        return False
    else:
        print(f"  ✅ STATIC_ROOT configurado: {static_root}")
        return True


def check_media_files():
    """Verifica que los archivos media estén configurados"""
    print("\n📸 Verificando Archivos Media...")
    media_root = settings.MEDIA_ROOT
    if not media_root:
        print("  ⚠️  MEDIA_ROOT no configurado")
        return False
    else:
        print(f"  ✅ MEDIA_ROOT configurado: {media_root}")
        return True


def check_security_settings():
    """Verifica configuraciones de seguridad"""
    print("\n🔒 Verificando Configuraciones de Seguridad...")
    issues = []
    
    if settings.DEBUG:
        print("  ⚠️  DEBUG=True (configuraciones de seguridad deshabilitadas)")
        return True  # No es un error si está en desarrollo
    
    # Verificar configuraciones de seguridad
    security_settings = {
        'SECURE_SSL_REDIRECT': getattr(settings, 'SECURE_SSL_REDIRECT', None),
        'SESSION_COOKIE_SECURE': getattr(settings, 'SESSION_COOKIE_SECURE', None),
        'CSRF_COOKIE_SECURE': getattr(settings, 'CSRF_COOKIE_SECURE', None),
    }
    
    all_secure = all(security_settings.values())
    if all_secure:
        print("  ✅ Configuraciones de seguridad habilitadas")
    else:
        print("  ⚠️  Algunas configuraciones de seguridad no están habilitadas")
        for key, value in security_settings.items():
            if not value:
                print(f"     - {key}: False")
    
    return True


def generate_secret_key():
    """Genera una nueva SECRET_KEY"""
    print("\n🔑 Generando nueva SECRET_KEY...")
    new_key = get_random_secret_key()
    print(f"\n  Nueva SECRET_KEY generada:")
    print(f"  {new_key}")
    print("\n  💡 Copia esta clave y configúrala en tu variable de entorno SECRET_KEY")


def main():
    """Función principal"""
    print("=" * 60)
    print("🔍 Verificación de Configuración de Despliegue")
    print("=" * 60)
    
    checks = [
        check_secret_key,
        check_debug,
        check_allowed_hosts,
        check_database,
        check_redis,
        check_cors,
        check_static_files,
        check_media_files,
        check_security_settings,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Error ejecutando verificación: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 Resumen")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ Todas las verificaciones pasaron ({passed}/{total})")
        print("\n🎉 Tu aplicación está lista para producción!")
    else:
        print(f"⚠️  {passed}/{total} verificaciones pasaron")
        print("\n💡 Revisa los problemas indicados arriba")
    
    print("\n" + "=" * 60)
    print("💡 Comandos útiles:")
    print("=" * 60)
    print("  Generar SECRET_KEY:")
    print("    python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\"")
    print("\n  Recopilar archivos estáticos:")
    print("    python manage.py collectstatic --noinput")
    print("\n  Ejecutar migraciones:")
    print("    python manage.py migrate")
    print("\n  Crear superusuario:")
    print("    python manage.py createsuperuser")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--generate-key':
        generate_secret_key()
    else:
        main()





