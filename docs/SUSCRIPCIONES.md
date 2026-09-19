# Suscripciones mensuales

Implementación para la rama dev de Belleza Integral.

## Alcance

Se agregan:

- Planes de suscripción mensual.
- Alta de membresía por cliente autenticado.
- Renovación manual.
- Cancelación inmediata.
- Historial de pagos demostrativos.
- Consulta de beneficios de membresía.
- Administración de planes y suscripciones.
- Auditoría mediante auditoria_cambios.
- Pruebas de integración.

Los pagos son demostrativos y no realizan cargos bancarios reales. La aplicación
solo conserva los últimos cuatro dígitos ficticios cuando se selecciona
tarjeta_simulada.

## Instalación de base de datos

Desde la raíz del repositorio:

    python scripts/instalar_suscripciones.py

Validación sin modificar:

    python scripts/instalar_suscripciones.py --solo-verificar

Después:

    python start_server.py

Verificación HTTP:

    GET /api/v1/health/suscripciones

## Endpoints públicos

    GET /api/v1/planes-suscripcion
    GET /api/v1/health/suscripciones

## Endpoints cliente

    GET   /api/v1/suscripciones/mia
    GET   /api/v1/suscripciones/mis-pagos
    GET   /api/v1/suscripciones/beneficios
    POST  /api/v1/suscripciones
    POST  /api/v1/suscripciones/{id}/renovar
    PATCH /api/v1/suscripciones/{id}/cancelar

## Endpoints administrador

    GET   /api/v1/admin/planes-suscripcion
    POST  /api/v1/admin/planes-suscripcion
    PUT   /api/v1/admin/planes-suscripcion/{id}
    PATCH /api/v1/admin/planes-suscripcion/{id}/estado
    GET   /api/v1/admin/suscripciones
    GET   /api/v1/admin/pagos-suscripcion
    POST  /api/v1/admin/suscripciones/marcar-vencidas

## Contratar

    POST /api/v1/suscripciones

Ejemplo:

    {
      "plan_id": 1,
      "metodo_pago": "efectivo",
      "clave_operacion": "alta_membresia_0001"
    }

El usuario se obtiene del JWT. No se acepta usuario_id enviado por el cliente.

## Regla de vigencia

Una membresía otorga beneficios únicamente cuando:

    estado = activa
    fecha_inicio <= NOW()
    fecha_fin > NOW()

La vista vw_suscripciones_activas aplica esta regla incluso antes de ejecutar
la actualización administrativa de vencimientos.

## Descuentos

El endpoint /suscripciones/beneficios ya expone los porcentajes contratados.
Esta entrega no modifica todavía el total de pedidos ni el precio de citas.
Para aplicar descuentos reales debe definirse previamente cómo conviven
membresía, promociones y canje de puntos.


## Instalación en MySQL remoto

La migración remota también está versionada en Git. El archivo SQL continúa
siendo:

    database/008_suscripciones.sql

Para ejecutarlo contra un hosting MySQL remoto se utiliza:

    scripts/instalar_suscripciones_remoto.py

### Opción recomendada: archivo local de conexión

Copia el ejemplo:

    copy .env.remote.example .env.remote

Edita solamente `.env.remote` con host, puerto, base y usuario. Este archivo
está excluido de Git.

No es obligatorio guardar la contraseña. Si no defines
`REMOTE_DB_PASSWORD`, el instalador la solicitará sin mostrarla.

Primero verifica conectividad y prerrequisitos:

    python scripts/instalar_suscripciones_remoto.py --verify

Para aplicar la migración:

    python scripts/instalar_suscripciones_remoto.py --apply

El modo `--apply` vuelve a verificar automáticamente al finalizar. También puedes comprobar después con:\n\n    python scripts/instalar_suscripciones_remoto.py --verify\n\nLa verificación comprueba:

- 3 tablas;
- 2 vistas;
- triggers del módulo;
- plan inicial.

### Opción sin archivo .env.remote

También puedes indicar la conexión en el comando:

    python scripts/instalar_suscripciones_remoto.py ^
      --host HOST_MYSQL ^
      --port 3306 ^
      --database BASE_DATOS ^
      --user USUARIO ^
      --apply

La contraseña se solicita interactivamente. No se recomienda usar
`--password` porque puede quedar almacenada en el historial de comandos.

### Requisitos del usuario MySQL remoto

El usuario debe poder crear tablas, vistas y triggers, además de ejecutar
INSERT/UPDATE/SELECT sobre la base de Belleza Integral. El script no intenta
crear ni seleccionar otra base con CREATE DATABASE/USE.


## Mi cuenta

Para clientes, la pantalla **Mi cuenta** consulta también
`GET /api/v1/suscripciones/mia`.

Si existe una membresía activa muestra:

- nombre del plan;
- estado activo;
- fecha de vencimiento;
- descuento de productos;
- descuento de servicios;
- acceso directo a "Mi suscripción".

Si no existe una membresía activa muestra un acceso para consultar los planes.

## Descuento de productos

`GET /api/v1/productos` continúa siendo público. Cuando la solicitud lleva un
JWT válido de cliente con membresía activa, cada producto incluye:

    precio_original
    precio
    descuento_suscripcion

El campo `precio` es el precio final después del descuento.

El checkout no confía en el precio mostrado por JavaScript. Al crear
`POST /api/v1/pedidos`, el backend vuelve a consultar la membresía activa,
recalcula el precio y guarda el valor descontado en
`pedido_detalle.precio_unitario`.
