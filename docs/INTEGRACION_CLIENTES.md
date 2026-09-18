# Contrato para el website y la aplicación móvil

Versión de entrega 1.1.1. Prefijo estable /api/v1. El contrato exhaustivo, cuerpos,
filtros y respuestas están en openapi.json; ejemplos editables en Postman.

## Decisiones comunes

- Los clientes hablan HTTP/JSON con Flask; únicamente el backend usa MySQL.
- La URL de API es configurable por ambiente. 127.0.0.1 en un teléfono es el teléfono,
  no el PC. Para desarrollo en la misma red, usar la IP del PC y el puerto 5000.
- Website servido por otro origen: configurar CORS_ORIGINS en .env con orígenes exactos
  separados por comas (protocolo, host y puerto; sin ruta final ni comodín).
- API autenticada: Authorization: Bearer <access_token>. Login entrega expires_in;
  actualmente 1800 segundos. No hay refresh token. Un 401 requiere nuevo login.
- Logout, cambio de contraseña/rol y desactivación revocan las sesiones correspondientes.
  Reactivar una cuenta no recupera sus tokens antiguos.
- No guardar contraseñas ni incluir tokens en URL, informes, capturas o repositorios.
- Dinero: texto decimal, por ejemplo "135.00". No calcular totales autoritativos en cliente.
- Fechas de citas: YYYY-MM-DD; horas HH:MM, zona America/Guatemala. No convertir
  inadvertidamente una hora de cita a UTC desde el selector del dispositivo.
- JSON usa success, message y data; algunas listas añaden meta. Los endpoints antiguos
  no tienen exactamente los mismos campos de paginación que los nuevos: seguir OpenAPI.

## Flujos y operaciones

| Flujo de interfaz | Secuencia de API |
|---|---|
| Registro/login | POST /auth/registro → POST /auth/login → GET /auth/perfil |
| Reservar | GET /servicios → GET /personal → GET /disponibilidad → POST /citas |
| Mis citas | GET /citas/mias → PATCH /citas/{id}/reprogramar o /cancelar |
| Agenda del profesional | GET /agenda → PATCH /agenda/{id}/estado |
| Checkout simulado | GET /productos → POST /pedidos → GET /pedidos/mios |
| Fidelización | GET /promociones y /puntos → POST /puntos/canjear → GET /puntos/historial |
| Administración | GET /admin/usuarios, /admin/citas, /admin/servicios, /admin/productos y módulos asociados |
| Reporte | GET /admin/reportes/resumen → GET /admin/reportes/citas.xlsx |

En la tabla se omite /api/v1. Los permisos nunca dependen de ocultar un botón: el
servidor valida el rol y la propiedad del registro.

## Reintentos y errores

| Respuesta | Comportamiento de cliente |
|---|---|
| 400 / 415 | Mostrar validación y corregir entrada/formato; no repetir automáticamente |
| 401 | Limpiar sesión local y presentar login |
| 403 | Informar falta de permiso; no intentar otra identidad |
| 404 | Registro inexistente o no accesible por esa cuenta |
| 409 | Refrescar disponibilidad/stock/estado y pedir una nueva selección |
| 429 | Respetar Retry-After; no repetir en bucle |
| 500 / 503 o timeout | Informar incertidumbre; consultar el estado antes de repetir una escritura |

Para pedidos y canjes, generar clave_operacion una vez por intención del usuario y
conservarla durante los reintentos con el mismo cuerpo. Una clave con otro cuerpo
puede devolver 409. Para una nueva operación usar otra clave. Las reservas no tienen
esta clave: después de un timeout consultar mis citas antes de volver a reservar.

Completar una cita solo después de su hora final. Reprogramar la devuelve a pendiente.
Disponibilidad es orientativa hasta que la transacción confirma la reserva; otra
persona puede ocupar el horario entre la consulta y el envío.

## Criterios de integración

El website y Android deben cubrir carga, vacío, error, sesión expirada, falta de
permiso y conflicto concurrente. Probar al menos un ciclo reserva/reprogramación/
cancelación y un pedido con reintento. No conectar la suite destructiva a los datos
del salón. Producción requiere HTTPS y validación en el ambiente de publicación.
