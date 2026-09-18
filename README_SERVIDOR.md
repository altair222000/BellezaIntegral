# Belleza Integral - despliegue en servidor

Esta versión fue adaptada para trabajar con el esquema base de `database/database.sql` y con la capa de integridad/auditoría incorporada en `database/006_integridad_auditoria.sql` y `database/007_compatibilidad_api.sql`.

## Requisitos

- Python 3.11 o superior.
- MySQL 8.0 o superior. La capa de integridad utiliza `JSON_TABLE`, funciones JSON, `SIGNAL`, triggers, vistas y procedimientos almacenados.
- Una cuenta MySQL con permisos sobre la base del proyecto. Para instalar la capa de integridad debe poder crear `TRIGGER`, `VIEW`, `PROCEDURE` y `FUNCTION`.

## 1. Base de datos

### Base nueva

Importe primero `database/database.sql`. Este archivo corresponde exactamente al script base entregado para el proyecto y contiene `DROP TABLE`, por lo que no debe ejecutarse sobre una base con información que se quiera conservar.

Después configure `.env` y ejecute:

```bash
python scripts/instalar_integridad.py
```

El instalador aplica, en orden:

1. `database/006_integridad_auditoria.sql`
2. `database/007_compatibilidad_api.sql`

El instalador trabaja sobre `DB_NAME`; no intenta crear ni cambiar de base de datos. Esto permite usarlo en hosting compartido donde `CREATE DATABASE` suele estar restringido.

### Base existente

Si la base ya contiene el esquema de `database/database.sql`, NO vuelva a importar el dump. Configure `.env` y ejecute únicamente:

```bash
python scripts/instalar_integridad.py
```

Para validar una instalación ya realizada:

```bash
python scripts/instalar_integridad.py --solo-verificar
```

La verificación espera las 2 tablas de auditoría, 5 vistas, al menos 40 triggers y las 10 rutinas operativas (procedimientos/funciones).

## 2. Entorno Python

Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

No copie la `.venv` de otra computadora o de otro sistema operativo. Debe generarse nuevamente en el servidor.

## 3. Variables de entorno

Copie `.env.example` como `.env` y complete los valores reales:

```bash
cp .env.example .env
```

Variables mínimas:

```text
DB_HOST=
DB_PORT=3306
DB_NAME=
DB_USER=
DB_PASSWORD=
JWT_SECRET_KEY=
```

Si el proveedor MySQL exige TLS con CA, configure `DB_SSL_CA` con la ruta local del certificado.

## 4. Arranque

Arranque genérico:

```bash
python start_server.py
```

Por defecto escucha en `0.0.0.0:5000`. Las plataformas que proporcionan la variable `PORT` pueden usar el mismo comando; la aplicación la detecta automáticamente.

También puede usarse Waitress directamente:

```bash
waitress-serve --host=0.0.0.0 --port=5000 wsgi:app
```

El `Procfile` incluido usa `waitress-serve` y la variable `$PORT`.

## 5. Pruebas rápidas después del despliegue

Compruebe, en este orden:

```text
GET /api/v1/health
GET /api/v1/health/db
GET /api/v1/health/schema
```

El último endpoint debe informar:

- `tablas_auditoria = 2`
- `vistas = 5`
- `triggers >= 40`
- `rutinas = 10`

Un administrador puede consultar la auditoría mediante:

```text
GET /api/v1/admin/auditoria/cambios
GET /api/v1/admin/auditoria/eventos
```

Ambos endpoints aceptan paginación estándar (`pagina`, `limite`).

## Cambios de compatibilidad relevantes

- El stock ya no puede cambiarse libremente porque `trg_productos_bu_control_stock` lo bloquea. La API habilita la bandera de control únicamente dentro de las transacciones de inventario/pedidos y la limpia al finalizar.
- Los puntos ya no pueden modificarse libremente porque `trg_usuarios_bu_control_puntos` lo bloquea. La API conserva `cita_id`, `promocion_id` y `clave_operacion`, pero abre la autorización solamente durante el movimiento correspondiente.
- Cada transacción iniciada por la aplicación configura `@app_usuario_id`, `@app_ip` y `@app_correlacion_id`, de manera que los triggers de auditoría puedan identificar el contexto de la operación.
- Se corrigió `sp_crear_cita` para llenar `citas.duracion_min`, columna obligatoria del esquema actual.
- Se corrigió `sp_confirmar_pedido` para llenar `pedidos.clave_operacion` y `pedidos.solicitud_hash`, columnas obligatorias del esquema actual.
- Los triggers de citas ahora usan `citas.duracion_min` para citas existentes, conservando la duración histórica aunque posteriormente se edite la duración de un servicio.
- La transición `confirmada -> pendiente` se permite únicamente cuando la cita realmente cambia de fecha, hora o personal; esto mantiene compatible el flujo de reprogramación sin abrir una transición de estado libre.
- `vw_promociones_vigentes` incluye `puntos_costo`, requerido por la funcionalidad de canje del frontend.

## Seguridad operativa

- No publique `.env` ni lo incluya en repositorios.
- Use una contraseña MySQL exclusiva para la aplicación y una `JWT_SECRET_KEY` larga y aleatoria.
- Exponga la aplicación detrás de HTTPS en producción.
- Si frontend y API están en dominios distintos, configure `CORS_ORIGINS` con orígenes exactos separados por coma.
- Las tablas `auditoria_cambios`, `auditoria_eventos`, `puntos_historial` y `movimientos_inventario` son inmutables por diseño; no deben limpiarse mediante `DELETE` en producción.
