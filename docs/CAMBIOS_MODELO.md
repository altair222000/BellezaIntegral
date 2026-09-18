# Cambios al modelo documentado

La entrega revisada definía diez tablas y 75 atributos. El código anterior ya había
agregado citas.duracion_min como duración histórica. Esta versión conserva las diez
tablas de negocio y agrega dos tablas técnicas para sesiones. No se eliminan registros.

| Tabla | Adición | Motivo |
|---|---|---|
| citas | duracion_min (ya existente) | Conservar el intervalo reservado aunque cambie el servicio |
| promociones | puntos_costo INT UNSIGNED DEFAULT 0 | Definir un costo objetivo de canje; cero significa publicación sin canje |
| pedidos | clave_operacion VARCHAR(64) | Reintento idempotente por usuario; UK(usuario_id, clave_operacion) |
| pedidos | solicitud_hash CHAR(64) | Rechazar el uso de la misma clave con otro contenido |
| puntos_historial | cita_id INT UNSIGNED NULL, FK y UK | Una asignación por cita completada |
| puntos_historial | promocion_id INT UNSIGNED NULL, FK | Identificar el beneficio canjeado |
| puntos_historial | clave_operacion VARCHAR(64) NULL | Reintentos de canje sin descontar otra vez; UK(usuario_id, clave_operacion) |
| tokens_revocados | jti VARCHAR(64) PK; expira BIGINT | Cierre persistente de una sesión |
| sesiones_usuario | usuario_id INT UNSIGNED PK/FK; version INT UNSIGNED | Invalidar sesiones anteriores al cambiar contraseña o rol, o desactivar la cuenta |

Las ocho tablas nuevas se crean con database/005_completar_api.sql. Son seis de
negocio que aún no existían en el ZIP y dos técnicas. El script no altera las tablas
usuarios, servicios, disponibilidades ni citas.

Las promociones y citas ahora sí tienen relaciones explícitas con puntos_historial.
Estas dos FK son nuevas respecto a la entrega revisada: deben aparecer en el DER.
El campo motivo conserva una descripción del movimiento/canje, pero no es una
instantánea completa de todas las condiciones de la promoción.

El migrador comprueba nombres de columnas de tablas nuevas ya existentes y se
detiene si encuentra diferencias; no convierte silenciosamente una tabla de otra
versión. No es un comparador exhaustivo de tipos, índices o constraints. La suite
crea un esquema limpio y comprueba los comportamientos transaccionales.

Las sentencias DDL se confirman individualmente en MySQL. Repetir la migración crea
las tablas faltantes; no elimina las ya creadas. Restaurar archivos del parche no
borra las tablas nuevas ni revierte las operaciones realizadas desde la API.

Mantenimiento posterior: los registros de tokens_revocados con expira anterior a
UNIX_TIMESTAMP() se pueden purgar periódicamente; no contienen contraseñas ni tokens
completos. El funcionamiento no depende de purgarlos inmediatamente.
