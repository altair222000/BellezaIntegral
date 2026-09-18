# Website 02 — Mi cuenta y Mis citas

## Entregado

- Perfil con correo, teléfono, rol y puntos del cliente. Editar datos actualiza también el nombre de la cabecera.
- Cambio de contraseña con repetición de la nueva clave. Solo actual/nueva llegan al backend. El cambio cierra la sesión.
- Citas como tarjetas con profesional, fecha, hora de Guatemala, duración y estado legible.
- Reprogramación con fecha y selección de intervalos disponibles; el horario actual se muestra deshabilitado.
- Al cambiar la fecha se invalida la selección anterior. Guardar vuelve la cita a pendiente.
- Mensajes para falta de horarios, recursos no disponibles y conflictos al guardar.

## Extensión de API 1.1.2

GET /api/v1/citas/{cita_id}/disponibilidad?fecha=YYYY-MM-DD

Solo el cliente propietario puede consultar esta ruta. Una cita ajena se responde
como no encontrada. Se conserva la duración histórica, se excluye la cita actual
y se filtran las otras citas del cliente y del profesional. La consulta no reserva
un intervalo: PATCH /citas/{id}/reprogramar comprueba otra vez al escribir.

La ruta requiere cita pendiente/confirmada que no haya comenzado y recursos activos.
No incorpora tablas ni cambia las existentes. OpenAPI y Postman se actualizan; el
contrato pasa a 63 operaciones. La disponibilidad pública conserva su comportamiento.

## Aceptación local

1. Mi cuenta muestra correo y teléfono por separado. Editar el nombre actualiza la cabecera.
2. Contraseñas nuevas distintas producen un error sin enviar el cambio. Un cambio válido solicita nuevo login.
3. Mis citas muestra tarjetas sin una tabla horizontal ancha en móvil.
4. Reprogramar carga horarios para una cita futura propia. Guardar permanece deshabilitado hasta seleccionar uno distinto.
5. Cambiar la fecha limpia la selección anterior. Cerrar el diálogo no modifica la cita.
6. Un cambio confirmado conserva el ID y vuelve a pendiente. El profesional puede confirmarlo de nuevo.
7. Refrescar conserva una sesión vigente. VERIFICAR.cmd debe seguir aprobando el contrato y consultas.

## Evidencia y límites

17 pruebas pasaron en MySQL aislado, incluidas dos nuevas de reprogramación: duración
histórica, exclusión propia, conflicto con otra cita del cliente, permisos y conflicto
entre consulta y guardado. También se ejecutaron pruebas DOM de perfil, contraseña,
reprogramación, respuesta tardía al cerrar y regresión del inicio/catálogo/sesión.
Las pruebas DOM simulan respuestas HTTP. No equivalen a una revisión visual real en
Windows o teléfono; esa aceptación sigue a cargo de la instalación local.

Para repetir las pruebas API, usar únicamente una BD aislada terminada en _test con
el procedimiento ya documentado en PRUEBAS.md. La suite limpia sus tablas de prueba.
Los datos del salón no se usaron para las verificaciones de esta entrega.
