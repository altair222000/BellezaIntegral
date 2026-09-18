# Cambios realizados para la nueva base de datos

## Base recibida

`database/database.sql` coincide byte por byte con el script base proporcionado para esta adaptación.

## Capa nueva detectada

El script de integridad recibido incorpora:

- 2 tablas de auditoría.
- 5 vistas.
- 8 procedimientos en el archivo (uno de ellos es auxiliar y se elimina al terminar la creación de índices).
- 3 funciones.
- 40 triggers.

## Ajustes en la API

1. Control transaccional de cambios de stock.
2. Control transaccional de cambios de puntos.
3. Contexto de auditoría por transacción (usuario, IP y correlación).
4. Conversión de errores `SIGNAL SQLSTATE '45000'` a respuestas HTTP 409 legibles.
5. Consulta pública de promociones mediante `vw_promociones_vigentes`.
6. Endpoints de auditoría de solo lectura para administradores.
7. Endpoint `/api/v1/health/schema` para comprobar la instalación en el servidor.

## Correcciones SQL añadidas

`007_compatibilidad_api.sql` se ejecuta después de la capa recibida y corrige incompatibilidades sin borrar datos:

- `sp_crear_cita`: completa `duracion_min`.
- `sp_confirmar_pedido`: completa los campos obligatorios de idempotencia.
- triggers de citas: usan duración histórica almacenada en la cita para cálculos de solape y permiten `confirmada -> pendiente` únicamente cuando existe una reprogramación real.
- `vw_promociones_vigentes`: incluye `puntos_costo`.

El archivo original recibido se conserva en `database/original/` únicamente como referencia.
