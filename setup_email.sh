#!/bin/bash

# Script para configurar las variables de correo electrónico

echo "=========================================="
echo "Configuración de Correo Electrónico"
echo "=========================================="
echo ""

# Verificar si existe .env
if [ ! -f .env ]; then
    echo "Creando archivo .env desde .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✓ Archivo .env creado"
    else
        echo "⚠ .env.example no encontrado. Creando .env básico..."
        touch .env
    fi
    echo ""
fi

echo "Por favor, ingresa la siguiente información:"
echo ""

# Email del remitente
read -p "Email del remitente (ej: tu_correo@gmail.com): " EMAIL_USER
if [ -z "$EMAIL_USER" ]; then
    EMAIL_USER="tu_correo@gmail.com"
fi

# Contraseña de aplicación
read -p "Contraseña de aplicación o token SMTP: " EMAIL_PASSWORD
if [ -z "$EMAIL_PASSWORD" ]; then
    EMAIL_PASSWORD="tu_contraseña"
fi

# Host SMTP
read -p "Servidor SMTP (Enter para Gmail: smtp.gmail.com): " EMAIL_HOST
if [ -z "$EMAIL_HOST" ]; then
    EMAIL_HOST="smtp.gmail.com"
fi

# Puerto SMTP
read -p "Puerto SMTP (Enter para 587): " EMAIL_PORT
if [ -z "$EMAIL_PORT" ]; then
    EMAIL_PORT="587"
fi

# Nombre del remitente
read -p "Nombre del remitente (ej: Martial Arts Academy): " FROM_NAME
if [ -z "$FROM_NAME" ]; then
    FROM_NAME="Martial Arts Academy"
fi

# Actualizar o agregar variables en .env
echo ""
echo "Actualizando archivo .env..."

# Remover líneas existentes de email
sed -i.bak '/^EMAIL_/d' .env
sed -i.bak '/^DEFAULT_FROM_EMAIL/d' .env

# Agregar nuevas configuraciones
cat >> .env << EOF

# Configuración de Correo Electrónico
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=$EMAIL_HOST
EMAIL_PORT=$EMAIL_PORT
EMAIL_USE_TLS=True
EMAIL_HOST_USER=$EMAIL_USER
EMAIL_HOST_PASSWORD=$EMAIL_PASSWORD
DEFAULT_FROM_EMAIL=$FROM_NAME <$EMAIL_USER>
EOF

# Limpiar backup
rm -f .env.bak

echo ""
echo "✓ Configuración de correo actualizada en .env"
echo ""
echo "Para aplicar los cambios, reinicia el contenedor:"
echo "  docker-compose restart web"
echo ""
echo "Para más información, consulta EMAIL_SETUP.md"


