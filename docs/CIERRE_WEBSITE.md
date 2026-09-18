# Belleza Integral — cierre del website previo a APK

## Alcance acordado para esta entrega
- Usuarios, roles y perfiles: administrador, personal y cliente.
- Servicios, horarios, reservas, reprogramación, cancelación y agenda.
- Productos de venta e insumos, movimientos de inventario y pedidos demostrativos.
- Promociones y puntos; asignación administrativa por cita completada.
- Recordatorios consultables en aplicación para las siguientes 24 horas.
- Consulta de clientes, historial de citas, reportes y exportación XLSX.
- Website adaptable como cliente de las APIs existentes. APK: siguiente entrega.

No se incluyen cobros reales, transportista, correos, WhatsApp ni notificaciones push.
Un pedido «completado» representa la operación demostrativa registrada, no prueba
que un transportista haya entregado un producto.
El canje tiene una referencia y se entrega manualmente en el salón. No existe
un estado informático de entrega ni descuento automático en pedidos. Las cremas
canjeadas no descuentan inventario automáticamente; registrar su salida manual
con la referencia del canje si el beneficio consume un producto físico.
Política inicial propuesta: administrador asigna 100 puntos por atención completada,
una asignación por cita. La cantidad sigue siendo configurable en el formulario.

## Bonificación de prueba solicitada
El script agrega 100 puntos a cliente.dos@example.com, no reemplaza el saldo actual.
Registra motivo y referencia fija en puntos_historial sin asociarlos a una cita.
Si tenía 0, queda en 100; si tenía 50, queda en 150. Ejecutarlo de nuevo no vuelve
a sumar, incluso después de consumir los puntos. Conserva los movimientos anteriores.
La API normal de asignación sigue exigiendo una cita completada.

## Novedades de este paquete
- Menú Recordatorios para cliente y personal; botón de actualización.
- Menú Clientes para administración: búsqueda literal por nombre/correo/teléfono,
  saldo y consulta paginada del historial de citas.
- Menú Movimientos de inventario para consultar entradas y salidas.
- Carga única de puntos, verificación local y guía de aceptación.
No modifica las reglas horarias de la agenda ni amplía el contrato de la API.

## Estado de entrega
Implementación del bloque preparada y probada en entorno aislado. La aceptación
final depende de ejecutar la matriz adjunta contra la instalación del usuario.
La APK todavía no se ha construido. No se declara entrega móvil ni producción.
