# Script de Población de Datos de Prueba

Este script permite poblar la base de datos con datos de prueba realistas para facilitar el desarrollo y las pruebas del sistema.

## Uso

### Ejecutar dentro del contenedor Docker

```bash
# Entrar al contenedor
docker compose exec web bash

# Ejecutar el script con valores por defecto
python manage.py populate_test_data

# Ejecutar con opciones personalizadas
python manage.py populate_test_data \
  --users 100 \
  --instructors 10 \
  --classes 200 \
  --blog 50 \
  --resources 60 \
  --gallery 15 \
  --events 20 \
  --exams 15
```

### Ejecutar desde fuera del contenedor

```bash
docker compose exec web python manage.py populate_test_data
```

## Opciones Disponibles

| Opción | Descripción | Valor por defecto |
|--------|-------------|-------------------|
| `--users` | Número de estudiantes a crear | 50 |
| `--instructors` | Número de instructores a crear | 5 |
| `--classes` | Número de clases a crear | 100 |
| `--blog` | Número de posts de blog a crear | 30 |
| `--resources` | Número de recursos a crear | 40 |
| `--gallery` | Número de galerías a crear | 10 |
| `--events` | Número de eventos a crear | 15 |
| `--exams` | Número de sesiones de examen a crear | 10 |
| `--clear` | Eliminar todos los datos existentes antes de poblar | False |

## Ejemplos de Uso

### Población básica (valores por defecto)
```bash
python manage.py populate_test_data
```

### Población masiva para pruebas de rendimiento
```bash
python manage.py populate_test_data \
  --users 500 \
  --instructors 20 \
  --classes 1000 \
  --blog 100 \
  --resources 200 \
  --gallery 30 \
  --events 50 \
  --exams 30
```

### Limpiar y poblar desde cero
```bash
python manage.py populate_test_data --clear
```

### Población mínima para desarrollo rápido
```bash
python manage.py populate_test_data \
  --users 10 \
  --instructors 2 \
  --classes 20 \
  --blog 5 \
  --resources 10 \
  --gallery 3 \
  --events 5 \
  --exams 3
```

## Datos Creados

El script crea los siguientes tipos de datos:

### Usuarios
- **1 Admin**: `admin@test.com` / `admin123`
- **N Instructores**: `instructor1@test.com`, `instructor2@test.com`, etc. / `test123`
- **N Estudiantes**: `student1@test.com`, `student2@test.com`, etc. / `test123`

Cada usuario incluye:
- Perfil completo con información personal
- Cinturón aleatorio
- Dojo asignado
- Datos de contacto

### Clases
- Clases con diferentes tipos (regular, intensiva, privada, seminario, examen)
- Diferentes niveles de dificultad
- Reservas de estudiantes
- Asistencias registradas (para clases pasadas)
- Algunas clases canceladas (5%)

### Blog
- Posts con categorías y tags
- Comentarios en los posts
- Ratings (calificaciones) de los posts
- Algunos posts destacados (20%)

### Recursos
- Diferentes tipos (video, documento, enlace, imagen)
- Diferentes categorías y niveles
- Tags asociados
- Algunos recursos destacados (15%) y premium (20%)

### Galerías
- Galerías con múltiples elementos (imágenes/videos)
- Descripciones asociadas

### Eventos
- Eventos con diferentes categorías
- Participaciones de estudiantes
- Resultados variados (1er lugar, 2do lugar, participación, etc.)
- Algunos eventos verificados (70%)

### Exámenes
- Sesiones de examen para diferentes niveles de cinturón
- Participantes asignados
- Resultados con calificaciones por parámetros
- Algunos exámenes calificados (70%)

### Pagos
- Los pagos se crean automáticamente cuando se crean estudiantes (mediante señales)
- Configuración de cuota activa ($50, vencimiento día 10)

## Notas Importantes

1. **No elimina usuarios admin existentes**: El script no elimina usuarios superusuarios al usar `--clear`.

2. **Datos realistas**: Los datos generados son variados y realistas, incluyendo:
   - Nombres y apellidos españoles
   - Fechas distribuidas en el pasado y futuro
   - Relaciones coherentes entre entidades
   - Estadísticas variadas (vistas, descargas, etc.)

3. **Rendimiento**: Para grandes volúmenes de datos (más de 1000 registros), el proceso puede tardar varios minutos.

4. **Relaciones**: El script mantiene la integridad referencial, asegurando que todas las relaciones entre modelos sean válidas.

## Solución de Problemas

### Error: "No such file or directory"
Asegúrate de estar ejecutando el comando dentro del contenedor Docker o usando `docker compose exec`.

### Error: "Database is locked"
Espera a que otras operaciones de base de datos terminen antes de ejecutar el script.

### Datos duplicados
Usa la opción `--clear` para eliminar datos existentes antes de poblar nuevos datos.

## Personalización

Si necesitas modificar los datos generados, edita el archivo:
```
martial_arts_api/users/management/commands/populate_test_data.py
```

Puedes modificar las listas de datos de prueba al inicio del archivo:
- `FIRST_NAMES`, `LAST_NAMES`: Nombres para usuarios
- `DOJOS`: Nombres de dojos
- `BELT_RANKS`: Rangos de cinturones
- `CLASS_NAMES`: Nombres de clases
- `BLOG_CATEGORIES`, `BLOG_TAGS`: Categorías y tags del blog
- Y más...





