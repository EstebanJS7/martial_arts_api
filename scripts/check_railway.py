#!/usr/bin/env python
"""
Script para verificar configuración específica de Railway
Ejecutar: python scripts/check_railway.py
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

print("=" * 60)
print("🚂 Verificación de Configuración para Railway")
print("=" * 60)

# Verificar archivos necesarios
print("\n📁 Verificando archivos necesarios...")

required_files = {
    'railway.json': BASE_DIR / 'railway.json',
    'requirements.txt': BASE_DIR / 'requirements.txt',
    'manage.py': BASE_DIR / 'manage.py',
    'settings.py': BASE_DIR / 'martial_arts_api' / 'settings.py',
}

all_files_exist = True
for file_name, file_path in required_files.items():
    if file_path.exists():
        print(f"  ✅ {file_name}")
    else:
        print(f"  ❌ {file_name} - NO ENCONTRADO")
        all_files_exist = False

if not all_files_exist:
    print("\n⚠️  Algunos archivos necesarios no se encontraron")
    sys.exit(1)

# Verificar railway.json
print("\n📋 Verificando railway.json...")
try:
    import json
    railway_config_path = BASE_DIR / 'railway.json'
    with open(railway_config_path, 'r') as f:
        config = json.load(f)
    
    required_keys = ['build', 'deploy']
    for key in required_keys:
        if key in config:
            print(f"  ✅ {key} configurado")
        else:
            print(f"  ❌ {key} faltante")
    
    # Verificar startCommand
    if 'deploy' in config and 'startCommand' in config['deploy']:
        start_cmd = config['deploy']['startCommand']
        if 'daphne' in start_cmd and '$PORT' in start_cmd:
            print(f"  ✅ startCommand correcto: {start_cmd}")
        else:
            print(f"  ⚠️  startCommand puede necesitar ajustes: {start_cmd}")
except Exception as e:
    print(f"  ❌ Error leyendo railway.json: {e}")

# Verificar variables de entorno necesarias
print("\n🔐 Verificando variables de entorno...")
railway_env_vars = [
    'DATABASE_URL',
    'REDIS_URL',
    'SECRET_KEY',
    'DEBUG',
    'ALLOWED_HOSTS',
]

print("\n  Variables que Railway inyecta automáticamente:")
print("    ✅ DATABASE_URL (si agregas PostgreSQL)")
print("    ✅ REDIS_URL (si agregas Redis)")

print("\n  Variables que debes configurar manualmente:")
for var in ['SECRET_KEY', 'DEBUG', 'ALLOWED_HOSTS', 'CORS_ALLOWED_ORIGINS', 'FRONTEND_URL']:
    print(f"    ⚠️  {var} (configurar en Railway Dashboard)")

# Verificar estructura de directorios
print("\n📂 Verificando estructura de directorios...")
expected_dirs = [
    BASE_DIR / 'martial_arts_api',
    BASE_DIR / 'users',
    BASE_DIR / 'payments',
    BASE_DIR / 'classes',
]

for dir_path in expected_dirs:
    if dir_path.exists() and dir_path.is_dir():
        print(f"  ✅ {dir_path.name}/")
    else:
        print(f"  ⚠️  {dir_path.name}/ no encontrado")

# Verificar requirements.txt
print("\n📦 Verificando requirements.txt...")
requirements_path = BASE_DIR / 'requirements.txt'
if requirements_path.exists():
    with open(requirements_path, 'r') as f:
        requirements = f.read()
    
    critical_packages = ['Django', 'daphne', 'channels', 'celery', 'psycopg2']
    for package in critical_packages:
        if package.lower() in requirements.lower():
            print(f"  ✅ {package}")
        else:
            print(f"  ⚠️  {package} no encontrado en requirements.txt")
else:
    print("  ❌ requirements.txt no encontrado")

# Verificar settings.py
print("\n⚙️  Verificando configuración de settings.py...")
settings_path = BASE_DIR / 'martial_arts_api' / 'settings.py'
if settings_path.exists():
    with open(settings_path, 'r') as f:
        settings_content = f.read()
    
    # Verificar que use variables de entorno
    checks = {
        'os.getenv': 'Usa variables de entorno',
        'DATABASE_URL': 'Configuración de BD desde env',
        'REDIS_URL': 'Configuración de Redis desde env',
        'ALLOWED_HOSTS': 'ALLOWED_HOSTS configurado',
    }
    
    for check, description in checks.items():
        if check in settings_content:
            print(f"  ✅ {description}")
        else:
            print(f"  ⚠️  {description} - Verificar")

print("\n" + "=" * 60)
print("📊 Resumen")
print("=" * 60)
print("\n✅ Verificaciones completadas")
print("\n📝 Próximos pasos:")
print("  1. Asegúrate de que todos los archivos estén presentes")
print("  2. Configura las variables de entorno en Railway")
print("  3. Agrega PostgreSQL y Redis en Railway")
print("  4. Despliega el servicio")
print("\n📖 Ver guía completa: docs/GUIA_DESPLIEGUE_RAILWAY.md")
print("=" * 60)





