# Pruebas de aceptación local

Guardar captura de resultado por caso; anotar fecha, cuenta/rol y aprobado/fallido.
No incluir contraseñas ni tokens. No ejecutar consultas de prueba sobre otras bases.

| Caso | Acción | Resultado esperado |
|---|---|---|
| 01 | Ejecutar instalador y carga; ejecutar otra vez | 100 puntos añadidos una sola vez, misma referencia |
| 02 | Cliente dos: Mis puntos | Bonificación con motivo de prueba y saldo actualizado |
| 03 | Canjear promoción de 50 con saldo inicial 100 | Saldo 50, movimiento -50 y referencia |
| 04 | Intentar beneficio mayor al saldo | Botón deshabilitado y puntos faltantes |
| 05 | Cliente/personal: Recordatorios | Solo citas propias pendientes/confirmadas en siguientes 24 horas; vacío si no hay |
| 06 | Administrador: Clientes; buscar cliente.dos@example.com | Cliente correcto, saldo, historial de sus citas |
| 07 | Cliente: crear reserva y reprogramar a horario disponible | Nueva fecha/hora, sin solapamiento; estado según regla de reprogramación |
| 08 | Personal: confirmar cita y completar después de su fin | Estados correctos; antes del fin debe rechazar |
| 09 | Administrador: crear servicio y disponibilidad de prueba | Consulta pública y reserva utilizan los datos activos |
| 10 | Administrador: crear producto venta, entrada de 10; comprar 1 | Pedido con precio del servidor y stock 9 |
| 11 | Administrador: cancelar ese pedido de prueba | Stock 10, movimiento de reintegro, pedido cancelado |
| 12 | Volver a consultar pedido cancelado | Sin botón de nueva cancelación ni doble reintegro |
| 13 | Desactivar y reactivar cuenta de prueba | Acceso bloqueado al desactivar; requiere sesión válida al reactivar |
| 14 | Abrir ruta administrativa con cliente | API rechaza por permisos |
| 15 | Reportes: periodo de pedidos/citas; exportar XLSX | Totales coherentes y archivo legible |
| 16 | Refrescar pestaña cliente con sesión y carrito | Sesión y carrito en la misma pestaña se conservan |
| 17 | Teléfono en misma red: login, reserva, compra y puntos | Navegación usable y sin controles inaccesibles |

Usar pedidos/productos/cuentas de prueba para acciones de cancelación o estado.
No marcar como completada una atención futura para desbloquear la prueba: ahora
la bonificación de 100 permite probar el canje sin alterar ninguna cita.

Evidencias ya mostradas en conversación: reservas, confirmación, reprogramación,
consulta de agenda, pedido y detalle, ventas simuladas/stock y bloqueo de canje
por saldo cero. La bonificación, canje positivo y las pantallas nuevas requieren
comprobación local después de instalar.
