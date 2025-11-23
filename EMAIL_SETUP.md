# Configuración de Correo Electrónico

Este documento explica cómo configurar el envío de correos electrónicos en la aplicación.

## Variables de Entorno Requeridas

Las siguientes variables deben estar configuradas en tu archivo `.env`:

- `EMAIL_BACKEND`: Backend de correo a usar (por defecto: `django.core.mail.backends.smtp.EmailBackend`)
- `EMAIL_HOST`: Servidor SMTP (por defecto: `smtp.gmail.com`)
- `EMAIL_PORT`: Puerto SMTP (por defecto: `587`)
- `EMAIL_USE_TLS`: Usar TLS (por defecto: `True`)
- `EMAIL_HOST_USER`: Usuario/email del servidor SMTP
- `EMAIL_HOST_PASSWORD`: Contraseña o token de aplicación
- `DEFAULT_FROM_EMAIL`: Email que aparecerá como remitente

## Configuración para Gmail

### Paso 1: Habilitar verificación en 2 pasos
1. Ve a tu cuenta de Google: https://myaccount.google.com/
2. Activa la verificación en 2 pasos si no la tienes activada

### Paso 2: Crear una Contraseña de Aplicación
1. Ve a: https://myaccount.google.com/apppasswords
2. Selecciona "Aplicación" y "Correo"
3. Selecciona "Dispositivo" y elige "Otro (nombre personalizado)"
4. Escribe "Martial Arts API" y haz clic en "Generar"
5. Copia la contraseña de 16 caracteres generada

### Paso 3: Configurar en .env
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx  # La contraseña de aplicación de 16 caracteres (sin espacios)
DEFAULT_FROM_EMAIL=Martial Arts Academy <tu_correo@gmail.com>
```

## Configuración para Outlook/Office365

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_correo@outlook.com
EMAIL_HOST_PASSWORD=tu_contraseña
DEFAULT_FROM_EMAIL=Martial Arts Academy <tu_correo@outlook.com>
```

## Configuración para SendGrid

1. Crea una cuenta en SendGrid: https://sendgrid.com/
2. Genera una API Key en el panel de SendGrid
3. Configura en `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=tu_api_key_de_sendgrid
DEFAULT_FROM_EMAIL=Martial Arts Academy <noreply@tudominio.com>
```

## Configuración para Mailgun

1. Crea una cuenta en Mailgun: https://www.mailgun.com/
2. Obtén tus credenciales SMTP del panel
3. Configura en `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=postmaster@tu-dominio.mailgun.org
EMAIL_HOST_PASSWORD=tu_password_de_mailgun
DEFAULT_FROM_EMAIL=Martial Arts Academy <noreply@tudominio.com>
```

## Configuración para Desarrollo Local (Console Backend)

Para desarrollo local, puedes usar el backend de consola que imprime los correos en la terminal:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

## Configuración para Desarrollo Local (File Backend)

Para guardar los correos en archivos locales:

```env
EMAIL_BACKEND=django.core.mail.backends.filebased.EmailBackend
EMAIL_FILE_PATH=/app/media/emails  # Ruta donde se guardarán los correos
```

## Verificar la Configuración

Después de configurar las variables, reinicia el contenedor Docker:

```bash
docker-compose restart web
```

Puedes probar el envío de correos usando el formulario de contacto en la landing page.

## Solución de Problemas

### Error: "Authentication failed"
- Verifica que `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD` sean correctos
- Para Gmail, asegúrate de usar una "Contraseña de aplicación", no tu contraseña normal
- Verifica que la verificación en 2 pasos esté activada en Gmail

### Error: "Connection refused"
- Verifica que `EMAIL_HOST` y `EMAIL_PORT` sean correctos
- Asegúrate de que el firewall no esté bloqueando el puerto
- Para Gmail, el puerto debe ser 587 (TLS) o 465 (SSL)

### Los correos no se envían pero no hay error
- Verifica los logs del contenedor: `docker-compose logs web`
- Revisa que `DEFAULT_FROM_EMAIL` tenga un formato válido
- Verifica que los correos no estén en la carpeta de spam

