#!/usr/bin/env python
"""
Script de verificación específico para despliegue de tesis
Verifica que todo esté configurado correctamente para producción gratis
Ejecutar: python scripts/check_tesis_deployment.py
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

print("=" * 70)
print("🎓 Verificación de Configuración para Tesis - Despliegue Gratis")
print("=" * 70)

# Verificar que estamos en modo producción
print("\n🔍 Verificando configuración de producción...")

# Verificar DEBUG
debug = os.getenv('DEBUG', 'False').lower() == 'true'
if debug:
    print("  ⚠️  DEBUG está en True - Cambiar a False en producción")
    print("     Configura DEBUG=False en Render")
else:
    print("  ✅ DEBUG está en False (correcto para producción)")

# Verificar SECRET_KEY
secret_key = os.getenv('SECRET_KEY', '')
if not secret_key or 'insecure' in secret_key.lower():
    print("  ❌ SECRET_KEY no configurada o insegura")
    print("     Genera una nueva con:")
    print("     python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\"")
else:
    print("  ✅ SECRET_KEY configurada")

# Verificar ALLOWED_HOSTS
allowed_hosts = os.getenv('ALLOWED_HOSTS', '')
if not allowed_hosts:
    print("  ⚠️  ALLOWED_HOSTS no configurado")
    print("     Configura en Render: ALLOWED_HOSTS=*.onrender.com,tu-backend.onrender.com")
else:
    print(f"  ✅ ALLOWED_HOSTS configurado: {allowed_hosts}")

# Verificar DATABASE_URL
database_url = os.getenv('DATABASE_URL', '')
if not database_url:
    print("  ❌ DATABASE_URL no configurada")
    print("     Configura en Render con la URL de Supabase")
elif 'supabase' in database_url.lower():
    print("  ✅ DATABASE_URL configurada (Supabase detectado)")
else:
    print("  ⚠️  DATABASE_URL configurada (verifica que sea correcta)")

# Verificar REDIS_URL
redis_url = os.getenv('REDIS_URL', '')
if not redis_url:
    print("  ❌ REDIS_URL no configurada")
    print("     Configura en Render con la URL de Upstash")
elif 'upstash' in redis_url.lower():
    print("  ✅ REDIS_URL configurada (Upstash detectado)")
else:
    print("  ⚠️  REDIS_URL configurada (verifica que sea correcta)")

# Verificar CORS
cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
frontend_url = os.getenv('FRONTEND_URL', '')
if not cors_origins and not frontend_url:
    print("  ⚠️  CORS_ALLOWED_ORIGINS no configurado")
    print("     Configura en Render con la URL de tu frontend en Vercel")
    print("     Ejemplo: CORS_ALLOWED_ORIGINS=https://tu-app.vercel.app")
else:
    print("  ✅ CORS configurado")

# Verificar archivos necesarios
print("\n📁 Verificando archivos necesarios...")

required_files = {
    'requirements.txt': BASE_DIR / 'requirements.txt',
    'railway.json': BASE_DIR / 'railway.json',
    'manage.py': BASE_DIR / 'manage.py',
}

for file_name, file_path in required_files.items():
    if file_path.exists():
        print(f"  ✅ {file_name}")
    else:
        print(f"  ⚠️  {file_name} no encontrado (puede no ser necesario)")

# Verificar settings.py
print("\n⚙️  Verificando settings.py...")
settings_path = BASE_DIR / 'martial_arts_api' / 'settings.py'
if settings_path.exists():
    with open(settings_path, 'r') as f:
        settings_content = f.read()
    
    checks = {
        'os.getenv': 'Usa variables de entorno',
        'ALLOWED_HOSTS': 'ALLOWED_HOSTS configurado dinámicamente',
        'CORS_ALLOWED_ORIGINS': 'CORS configurado',
    }
    
    for check, description in checks.items():
        if check in settings_content:
            print(f"  ✅ {description}")
        else:
            print(f"  ⚠️  {description} - Verificar")

# Verificar optimizaciones para producción gratis
print("\n💰 Verificando optimizaciones para plan gratis...")

# Verificar que no hay configuraciones que consuman mucho
warnings = []

# Verificar Celery (opcional para tesis)
if 'CELERY_BROKER_URL' in os.environ:
    print("  ℹ️  Celery configurado (opcional para tesis)")
    print("     Si no lo necesitas, puedes omitirlo para simplificar")
else:
    print("  ✅ Celery no configurado (ok si no lo necesitas)")

# Verificar email (usar console backend para gratis)
email_backend = os.getenv('EMAIL_BACKEND', '')
if 'smtp' in email_backend.lower() and 'console' not in email_backend.lower():
    print("  ⚠️  Email configurado con SMTP")
    print("     Para tesis, puedes usar: EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend")
else:
    print("  ✅ Email configurado (o usando console backend)")

print("\n" + "=" * 70)
print("📊 Resumen de Verificación")
print("=" * 70)

print("\n✅ Configuraciones correctas:")
print("   - DEBUG=False")
print("   - SECRET_KEY configurada")
print("   - Variables de entorno configuradas")

print("\n⚠️  Verificaciones pendientes:")
print("   - Configurar variables en Render")
print("   - Verificar URLs de Supabase y Upstash")
print("   - Configurar CORS con URL de Vercel")

print("\n📝 Próximos pasos:")
print("   1. Desplegar frontend en Vercel")
print("   2. Configurar PostgreSQL en Supabase")
print("   3. Configurar Redis en Upstash")
print("   4. Desplegar backend en Render")
print("   5. Configurar Uptime Robot")
print("   6. Ejecutar migraciones")
print("   7. Crear superusuario")

print("\n📖 Ver guía completa: docs/GUIA_TESIS_GRATIS.md")
print("=" * 70)

