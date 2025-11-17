# Configuración de Redis

Redis es necesario para:
- **Channels**: WebSockets y notificaciones en tiempo real
- **Celery**: Tareas asíncronas y programadas (recordatorios)
- **Cache**: Caché de Django (opcional)

## Instalación de Redis

### Opción 1: Docker (Recomendado - Más fácil)

#### Windows
```bash
# Instalar Docker Desktop desde https://www.docker.com/products/docker-desktop
# Luego ejecutar:
docker run -d --name redis-martial-arts -p 6379:6379 redis:alpine
```

#### Linux/Mac
```bash
docker run -d --name redis-martial-arts -p 6379:6379 redis:alpine
```

Para iniciar Redis después de reiniciar:
```bash
docker start redis-martial-arts
```

### Opción 2: Instalación Nativa

#### Windows
1. Descargar Redis para Windows desde:
   - https://github.com/microsoftarchive/redis/releases
   - O usar WSL2 con Ubuntu y seguir instrucciones de Linux

2. Ejecutar `redis-server.exe`

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server  # Iniciar automáticamente al arrancar
```

#### Mac (Homebrew)
```bash
brew install redis
brew services start redis
```

## Verificar Instalación

### Verificar que Redis está ejecutándose
```bash
redis-cli ping
# Debe responder: PONG
```

### Ver información de Redis
```bash
redis-cli info
```

### Probar conexión desde Python
```bash
python manage.py shell
>>> import redis
>>> r = redis.Redis(host='localhost', port=6379, db=0)
>>> r.ping()
True
```

## Configuración en Django

La configuración ya está lista en `settings.py`:

### Para Channels (WebSockets)
```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('localhost', 6379)],
        },
    }
}
```

### Para Celery
```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

### Para Cache (Opcional)
Si quieres usar Redis para caché, puedes cambiar en `settings.py`:
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

## Configuración de Producción

### Variables de Entorno
Para producción, usa variables de entorno:

```python
# En settings.py
import os

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(os.getenv('REDIS_HOST', 'localhost'), int(os.getenv('REDIS_PORT', 6379)))],
        },
    }
}
```

### Redis con Autenticación
Si Redis tiene contraseña:
```python
CELERY_BROKER_URL = 'redis://:password@localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://:password@localhost:6379/0'
```

### Redis en Servidor Remoto
```python
CELERY_BROKER_URL = 'redis://usuario:password@redis.example.com:6379/0'
```

## Troubleshooting

### Error: "Connection refused"
- **Causa**: Redis no está ejecutándose
- **Solución**: 
  ```bash
  # Verificar si está ejecutándose
  redis-cli ping
  
  # Si no responde, iniciar Redis
  # Docker:
  docker start redis-martial-arts
  
  # Linux:
  sudo systemctl start redis-server
  
  # Mac:
  brew services start redis
  ```

### Error: "ModuleNotFoundError: No module named 'redis'"
- **Causa**: Falta instalar el paquete Python de Redis
- **Solución**:
  ```bash
  pip install redis
  # O si usas requirements.txt:
  pip install -r requirements.txt
  ```

### Error: "channels_redis.core.RedisChannelLayer"
- **Causa**: Falta instalar channels-redis
- **Solución**:
  ```bash
  pip install channels-redis
  ```

### Puerto 6379 ya en uso
- **Causa**: Otra instancia de Redis está usando el puerto
- **Solución**:
  ```bash
  # Ver qué proceso usa el puerto
  # Windows:
  netstat -ano | findstr :6379
  
  # Linux/Mac:
  lsof -i :6379
  
  # O cambiar el puerto en Docker:
  docker run -d -p 6380:6379 redis:alpine
  # Y actualizar settings.py con puerto 6380
  ```

### Redis se detiene después de cerrar terminal
- **Solución**: Ejecutar Redis como servicio
  ```bash
  # Docker (con --restart always):
  docker run -d --name redis-martial-arts --restart always -p 6379:6379 redis:alpine
  
  # Linux:
  sudo systemctl enable redis-server
  
  # Mac:
  brew services start redis
  ```

## Comandos Útiles de Redis

```bash
# Conectar a Redis CLI
redis-cli

# Ver todas las claves
redis-cli KEYS *

# Limpiar base de datos 0 (usado por Celery)
redis-cli FLUSHDB

# Limpiar base de datos 1 (usado por Channels)
redis-cli -n 1 FLUSHDB

# Ver información de memoria
redis-cli INFO memory

# Monitorear comandos en tiempo real
redis-cli MONITOR
```

## Verificación Final

Después de configurar Redis, verifica que todo funciona:

1. **Redis está ejecutándose**:
   ```bash
   redis-cli ping
   ```

2. **Channels funciona**:
   - Inicia el servidor Django
   - Las notificaciones WebSocket deberían funcionar

3. **Celery funciona**:
   ```bash
   celery -A martial_arts_api worker --loglevel=info
   # Debe iniciar sin errores
   ```

4. **Celery Beat funciona**:
   ```bash
   celery -A martial_arts_api beat --loglevel=info
   # Debe iniciar sin errores
   ```

## Notas Importantes

1. **Desarrollo**: Redis puede ejecutarse localmente
2. **Producción**: Considera usar Redis Cloud, AWS ElastiCache, o un servidor dedicado
3. **Seguridad**: En producción, configura autenticación y firewall
4. **Backup**: Redis puede persistir datos en disco (configuración por defecto)
5. **Rendimiento**: Redis es muy rápido, pero para alta carga considera clustering


