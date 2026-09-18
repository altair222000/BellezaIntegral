# Rutas y permisos

| Método | Ruta | Roles |
|---|---|---|
| GET | `/api/v1/admin/citas` | administrador |
| PATCH | `/api/v1/admin/citas/{cita_id}/estado` | administrador |
| GET | `/api/v1/admin/clientes` | administrador |
| GET | `/api/v1/admin/clientes/{cliente_id}/citas` | administrador |
| PUT | `/api/v1/admin/disponibilidades/{horario_id}` | administrador |
| PATCH | `/api/v1/admin/disponibilidades/{horario_id}/estado` | administrador |
| GET | `/api/v1/admin/inventario/movimientos` | administrador |
| POST | `/api/v1/admin/inventario/movimientos` | administrador |
| GET | `/api/v1/admin/pedidos` | administrador |
| PATCH | `/api/v1/admin/pedidos/{pedido_id}/cancelar` | administrador |
| POST | `/api/v1/admin/personal` | administrador |
| GET | `/api/v1/admin/personal/{personal_id}/disponibilidades` | administrador |
| GET | `/api/v1/admin/productos` | administrador |
| POST | `/api/v1/admin/productos` | administrador |
| PUT | `/api/v1/admin/productos/{producto_id}` | administrador |
| PATCH | `/api/v1/admin/productos/{producto_id}/estado` | administrador |
| GET | `/api/v1/admin/promociones` | administrador |
| POST | `/api/v1/admin/promociones` | administrador |
| PUT | `/api/v1/admin/promociones/{promocion_id}` | administrador |
| PATCH | `/api/v1/admin/promociones/{promocion_id}/estado` | administrador |
| POST | `/api/v1/admin/puntos/asignar` | administrador |
| GET | `/api/v1/admin/puntos/historial` | administrador |
| GET | `/api/v1/admin/reportes/citas.xlsx` | administrador |
| GET | `/api/v1/admin/reportes/resumen` | administrador |
| GET | `/api/v1/admin/servicios` | administrador |
| GET | `/api/v1/admin/usuarios` | administrador |
| POST | `/api/v1/admin/usuarios` | administrador |
| PATCH | `/api/v1/admin/usuarios/{usuario_id}` | administrador |
| PATCH | `/api/v1/admin/usuarios/{usuario_id}/estado` | administrador |
| PATCH | `/api/v1/admin/usuarios/{usuario_id}/rol` | administrador |
| GET | `/api/v1/admin/verificar` | administrador |
| GET | `/api/v1/agenda` | personal |
| PATCH | `/api/v1/agenda/{cita_id}/estado` | personal |
| POST | `/api/v1/auth/login` | Público |
| POST | `/api/v1/auth/logout` | administrador, personal, cliente |
| PATCH | `/api/v1/auth/password` | administrador, personal, cliente |
| GET | `/api/v1/auth/perfil` | administrador, personal, cliente |
| PATCH | `/api/v1/auth/perfil` | administrador, personal, cliente |
| POST | `/api/v1/auth/registro` | Público |
| POST | `/api/v1/citas` | cliente |
| PATCH | `/api/v1/citas/{cita_id}/cancelar` | cliente |
| PATCH | `/api/v1/citas/{cita_id}/reprogramar` | cliente |
| GET | `/api/v1/citas/mias` | cliente |
| GET | `/api/v1/disponibilidad` | Público |
| GET | `/api/v1/health` | Público |
| GET | `/api/v1/health/db` | Público |
| POST | `/api/v1/pedidos` | cliente |
| GET | `/api/v1/pedidos/{pedido_id}` | cliente, administrador |
| GET | `/api/v1/pedidos/mios` | cliente |
| GET | `/api/v1/personal` | Público |
| GET | `/api/v1/personal/{personal_id}/disponibilidades` | Público |
| POST | `/api/v1/personal/{personal_id}/disponibilidades` | administrador |
| GET | `/api/v1/productos` | Público |
| GET | `/api/v1/promociones` | Público |
| GET | `/api/v1/puntos` | cliente |
| POST | `/api/v1/puntos/canjear` | cliente |
| GET | `/api/v1/puntos/historial` | cliente |
| GET | `/api/v1/recordatorios` | cliente, personal |
| GET | `/api/v1/servicios` | Público |
| POST | `/api/v1/servicios` | administrador |
| PUT | `/api/v1/servicios/{servicio_id}` | administrador |
| PATCH | `/api/v1/servicios/{servicio_id}/estado` | administrador |

## Website 02 — API 1.1.2

GET /api/v1/citas/{cita_id}/disponibilidad?fecha=YYYY-MM-DD

Rol cliente, solo la cita propia. Excluye la cita consultada de los intervalos
ocupados, conserva su duración histórica y también filtra las otras citas del
cliente. Devuelve horarios en intervalos de 15 minutos; no reserva el horario.
PATCH /citas/{id}/reprogramar mantiene las comprobaciones transaccionales al guardar.

Errores: 400 filtros/fecha inválidos, 401 sesión inválida, 403 rol no permitido,
404 cita ajena/inexistente o recurso inactivo, 409 cita no reprogramable.
El contrato OpenAPI contiene 63 operaciones tras esta ampliación.
