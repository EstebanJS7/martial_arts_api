# Guía de Pruebas — `seed_demo_data`

Cómo probar el comando de datos demo antes y después de cargarlo en producción. Para referencia completa del comando (opciones, credenciales, seguridad) ver [POPULATE_TEST_DATA.md](POPULATE_TEST_DATA.md).

## 1. Prueba local (recomendada antes de Render)

Con el entorno local levantado y `DEBUG=True`:

```bash
# Primera carga
python manage.py seed_demo_data

# Verificar que es idempotente (no duplica)
python manage.py seed_demo_data

# Reset limpio y recarga
python manage.py seed_demo_data --reset-demo

# Volumen reducido para iterar rápido
python manage.py seed_demo_data --reset-demo --students 10 --weeks 6
```

### Checklist local

- [ ] El comando termina sin traceback y muestra el resumen final
- [ ] Correrlo dos veces seguidas NO duplica usuarios/clases/eventos
- [ ] `--reset-demo` elimina solo cuentas `*@demo.martial.local`
- [ ] Login con `admin.operations@demo.martial.local` / `DemoSeed2026!`

## 2. Prueba en Render (plan free, sin shell)

El seed corre vía `preDeployCommand` con doble llave de seguridad:

1. En Render → servicio backend → **Environment**, agregar temporalmente:

   ```env
   RUN_DEMO_SEED=true
   ALLOW_DEMO_SEED=true
   ```

2. **Manual Deploy → Deploy latest commit**
3. Observar los logs del predeploy: debe aparecer `migrate` y luego la salida del seed
4. Al terminar OK, **volver ambas variables a `false`** (si quedan en true, cada redeploy re-siembra datos demo)

> Si dejás solo `RUN_DEMO_SEED=true`, el predeploy falla adrede: es la salvaguarda, no un bug.

## 3. Verificación post-seed (producción)

Probar en orden, sin login primero:

| Endpoint | Esperado |
|---|---|
| `GET /api/users/public/stats/` | 200 con estadísticas |
| `GET /api/users/public/instructors/` | 200 con 3 instructores |
| `GET /api/classes/upcoming/` | 200 con clases futuras |
| `GET /api/blog/posts/?page=1&page_size=3` | 200 con posts |

Luego desde el frontend desplegado:

- [ ] Landing muestra clases, instructores, estadísticas y blog sin errores de consola
- [ ] Login admin: dashboard con datos (pagos, asistencia, gráficos)
- [ ] Login estudiante demo (ej. `student01.aldo.ayala@demo.martial.local`): mis clases, pagos, notificaciones
- [ ] Refresh con F5 en rutas internas (ej. `/dashboard`) no da 404

## 4. Errores comunes

| Síntoma | Causa probable |
|---|---|
| `CommandError` al sembrar cinturones | Catálogo real choca con el demo (mismo `name` u `order_number` con otro valor). Reconciliar manualmente |
| `DataError ... value too long` | Teléfonos >15 chars. Ya corregido en este comando; si aparece, revisar campos custom nuevos |
| Deploy falla en predeploy | Falta `ALLOW_DEMO_SEED=true` con `RUN_DEMO_SEED=true` |
| Datos viejos de fechas pasadas | Correr `--reset-demo`: las sesiones/eventos demo se podan por marcador |

## 5. Limpieza después de la demo

```bash
python manage.py seed_demo_data --reset-demo   # deja la base solo con datos reales
```

En Render (sin shell): mismo procedimiento del punto 2 pero ejecutando el reset. Si preferís dejar los datos para la presentación, simplemente no hacer nada: los datos demo son determinísticos y estables entre corridas.
