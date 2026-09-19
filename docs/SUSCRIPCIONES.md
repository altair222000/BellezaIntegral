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
