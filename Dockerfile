FROM python:3.12-slim

# Establecer directorio de trabajo
WORKDIR /app

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    python3-dev \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Copiar y hacer ejecutable el script de entrada
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
COPY docker-entrypoint.prod.sh /app/docker-entrypoint.prod.sh
RUN chmod +x /app/docker-entrypoint.sh /app/docker-entrypoint.prod.sh

# Crear directorio para archivos estáticos y media
RUN mkdir -p /app/staticfiles /app/media

# Exponer puerto
EXPOSE 8000

# Script de entrada
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Comando por defecto (puede ser sobrescrito en docker-compose)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "martial_arts_api.asgi:application"]

