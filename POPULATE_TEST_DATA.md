# Demo Seed Seguro

`populate_test_data` quedó desactualizado para un entorno productivo. Para demos realistas de tesis usá el nuevo comando seguro:

```bash
python manage.py seed_demo_data
```

## Qué hace

Genera o actualiza datos demo determinísticos para Paraguay, con foco en Ypané y Villeta:

- 1 superadmin demo
- 1 admin demo
- 3 instructores demo
- 24 a 30 estudiantes demo por defecto
- 2 academias/sedes demo
- 8 a 12 semanas de clases con pasado y futuro
- reservas, asistencia y waitlist
- pagos con estados variados y transacciones
- eventos, exámenes, blog, recursos y mensajes de contacto
- galería solo como metadata, sin subir archivos

## Seguridad

- No borra datos reales por defecto.
- Usa emails determinísticos `*@demo.martial.local` para aislar usuarios demo.
- `--reset-demo` elimina solamente datos demo creados por este comando.
- Si `DEBUG=False`, el comando aborta salvo que se cumplan AMBAS condiciones:
  - pasar `--allow-production`
  - definir `ALLOW_DEMO_SEED=true`

## Uso Local

```bash
python manage.py seed_demo_data
python manage.py seed_demo_data --reset-demo
python manage.py seed_demo_data --students 24 --weeks 8
```

Si corrés con Docker:

```bash
docker compose exec web python manage.py seed_demo_data
docker compose exec web python manage.py seed_demo_data --reset-demo
```

## Opciones

| Opción | Descripción | Default |
|---|---|---|
| `--students` | Cantidad de estudiantes demo determinísticos | `30` |
| `--instructors` | Cantidad de instructores demo determinísticos | `3` |
| `--weeks` | Semanas de calendario a generar | `10` |
| `--reset-demo` | Elimina solo datos demo antes de recrearlos | `False` |
| `--allow-production` | Requerido con `DEBUG=False` y `ALLOW_DEMO_SEED=true` | `False` |

## Credenciales Demo

- Password demo para todas las cuentas creadas: `DemoSeed2026!`
- Superadmin: `superadmin@demo.martial.local`
- Admin: `admin.operations@demo.martial.local`
- Instructores: `lorena.vera@demo.martial.local`, `miguel.ortega@demo.martial.local`, `noelia.ramirez@demo.martial.local`
- Estudiantes: `student01.aldo.ayala@demo.martial.local` hasta `student30.ernesto.narvaez@demo.martial.local` según la cantidad elegida

## Render Free Plan

Render free no ofrece shell interactiva, así que la forma segura es disparar el comando en `preDeployCommand` de manera TEMPORAL y con doble gating.

### Opción recomendada

1. Definí temporalmente estas variables en el servicio web:
   - `RUN_DEMO_SEED=true`
   - `ALLOW_DEMO_SEED=true`
2. Hacé un deploy manual.
3. Verificá el resultado en logs.
4. Volvé a dejar `RUN_DEMO_SEED=false` y `ALLOW_DEMO_SEED=false`.

Con la configuración actualizada de `render.yaml`, el deploy hace esto:

```bash
python3.12 manage.py migrate --noinput
if [ "$RUN_DEMO_SEED" = "true" ]; then
  python3.12 manage.py seed_demo_data --allow-production
fi
```

## Notas

- El comando evita `GalleryItem` con archivos para no depender de media local ni de uploads frágiles.
- Conserva catálogos compartidos como cinturones, disciplinas y parámetros de evaluación si ya existen.
- Hay una señal existente que crea pagos al crear perfiles con rol default `student`; el seed limpia esos pagos en admins/instructores demo para no contaminar producción.





## Advertencia sobre `RUN_DEMO_SEED` en Render

- Setear `RUN_DEMO_SEED=true` sin `ALLOW_DEMO_SEED=true` hace que el predeploy falle intencionalmente: el comando bloquea seeds en producción si falta esa variable (es una salvaguarda de diseño, no un error).
- Después de un deploy exitoso con seed, revertir ambas variables a `false` de inmediato para evitar reseeds accidentales en deploys siguientes.
