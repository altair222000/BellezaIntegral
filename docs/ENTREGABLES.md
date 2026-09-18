# Belleza Integral definición de entregables y cierre funcional de API

## Objetivo de esta entrega

Dejar una versión funcional de la API que permita avanzar a las interfaces web y
móvil sin continuar agregando rutas una por una durante cada prueba manual. La
versión 1.1.1 incorpora los módulos de los requisitos funcionales y un primer visor
responsivo conectado al backend. La aceptación final en la instalación del equipo
se registra con scripts/verificar_entrega.py y las pruebas de usuario.

La arquitectura adoptada en esta conversación es Flask como API REST compartida,
MySQL y clientes web/móvil. El visor se sirve desde Flask y consume JSON con fetch;
no requiere Node ni compilación para ejecutarse en Windows. Esto actualiza la
arquitectura Jinja2 sin API independiente descrita en la Entrega 7 revisada.

## Referencias revisadas

- Entrega 7.1 revisada: referencia principal para las diez tablas del negocio,
  restricciones, roles y checkout exclusivamente de demostración.
- Entrega 4: catálogo RF, RNF, RI, RR y reglas RRN.
- Entregas 5 y 6: diagramas UML estructurales y de comportamiento; deben ajustarse
  a la arquitectura REST y a las extensiones de esquema aquí documentadas. La
  revisión textual no equivale a una validación visual completa de sus diagramas.
- Sprint 0 y su lámina: backlog inicial y priorización; pagos reales y reseñas son
  elementos de prioridad baja. La Entrega 7 concreta los pagos como simulación.
- Entregas 2, 3 y documentos iniciales/unificados: objetivos del negocio y alcance
  de clientes, citas, comercialización, fidelización e información administrativa.

## Paquetes de entrega

| Entregable | Contenido | Criterio de aceptación | Estado de esta entrega |
|---|---|---|---|
| E1 API de cuentas y seguridad | Registro, login, logout, perfil, contraseña, roles, búsqueda, estado | Permisos por rol, datos propios, contraseñas con hash y sesiones revocables | Implementado y probado en entorno aislado |
| E2 API de servicios y agenda | Catálogo, horarios, disponibilidad, citas, reprogramación y estados | No solapar reservas; conservar duración; proteger citas ajenas | Implementado y probado en entorno aislado |
| E3 API de inventario y pedidos | Artículos, entradas/salidas, stock, checkout simulado y cancelación | Stock no negativo, detalle histórico e idempotencia de pedido | Implementado y probado en entorno aislado |
| E4 API de fidelización | Promociones, asignación, saldo, historial y canje | Una asignación por cita completada; canje vigente y saldo suficiente | Implementado y probado en entorno aislado |
| E5 Reportes y recordatorios internos | Resumen por período, XLSX, próximas citas en 24 horas | Reporte autorizado; exportación; consulta de recordatorios propios | Implementado; envío externo no incluido |
| E6 Contrato e integración | OpenAPI, colección Postman, rutas/roles y guía de conexión | Contrato válido, consumible desde web y cliente móvil | Entregado |
| E7 Visor web responsivo | Pantallas de cliente, personal y administración | Uso desde PC y teléfono, navegación por rol, flujos conectados | Implementado; pruebas visuales y aceptación en dispositivos pendientes |
| E8 Aplicación Android nativa | Interfaz y cliente HTTP que consume la misma API | Compilar, instalar y probar APK en dispositivo | Siguiente entrega, no se entrega APK aquí |
| E9 Documentación y pruebas | Matriz RF, extensiones de esquema, scripts, evidencia y seguimiento | Repetibilidad y separación entre pruebas ejecutadas y pendientes | Entregado |
| E10 Despliegue final | HTTPS, TLS MySQL, respaldos, monitoreo y CI/CD | Restauración comprobada y operación en ambiente elegido | Pendiente de infraestructura; no se declara producción |

## Matriz de requisitos funcionales

| Requisito | Implementación que lo cubre | Observación |
|---|---|---|
| RF-01 | POST /auth/login | JWT de 30 minutos |
| RF-02 | POST /admin/usuarios; PATCH /admin/usuarios/{id} | Mantiene también POST /admin/personal |
| RF-03 | PATCH /admin/usuarios/{id}/rol | No cambia el propio rol ni el de cuentas con historial asociado |
| RF-04 | POST /auth/registro | Rol cliente fijado en servidor |
| RF-05 | GET /admin/usuarios; PATCH /admin/usuarios/{id}; GET/PATCH /auth/perfil | Perfil propio o administrador |
| RF-06 | GET /admin/clientes?q= | Búsqueda literal por nombre, correo o teléfono |
| RF-07 | GET /admin/clientes/{id}/citas; GET /citas/mias | Historial con alcance por propietario |
| RF-08 | GET /disponibilidad | Guatemala, intervalos de 15 minutos |
| RF-09 | POST /citas | Cliente autenticado como propietario; un servicio y profesional |
| RF-10 | PATCH /citas/{id}/reprogramar | Cambia fecha/hora; vuelve a pendiente |
| RF-11 | PATCH /citas/{id}/cancelar; PATCH /admin/citas/{id}/estado | Administrador puede resolver citas de cuentas inactivas |
| RF-12 | GET /citas/mias; GET /agenda; GET /admin/citas | Vistas según rol |
| RF-13 | Transacciones y bloqueos de usuarios/citas | Prueba de dos reservas simultáneas incluida |
| RF-14 | PATCH /agenda/{id}/estado; PATCH /admin/citas/{id}/estado | Completar únicamente tras el fin |
| RF-15 a RF-18 | GET/POST /servicios; PUT /servicios/{id}; PATCH /servicios/{id}/estado | GET /admin/servicios incluye inactivos |
| RF-19 y RF-20 | POST/PUT /admin/productos | Diferencia venta e insumo; tipo permanente para conservar historial |
| RF-21 | POST /admin/inventario/movimientos | Cantidad, tipo y motivo; auditado por usuario |
| RF-22 | GET /admin/productos; GET /admin/inventario/movimientos | Existencia actual e historial |
| RF-23 | POST/PUT /admin/promociones; PATCH .../estado | Condiciones y vigencia |
| RF-24 | POST /admin/puntos/asignar | Cantidad definida por administrador; cita completada, una sola vez |
| RF-25 | GET /puntos; GET /puntos/historial | Solo saldo e historial propios |
| RF-26 | POST /puntos/canjear | Beneficio vigente y costo definido; no duplica descuento de puntos |
| RF-27 | GET /admin/reportes/resumen | Período máximo 366 días |
| RF-28 exportación | GET /admin/reportes/citas.xlsx | XLSX; hasta 10000 filas por exportación |
| RF-28 panel | Reportes, usuarios, citas e inventario en el visor | Se conserva el ID duplicado de la fuente, diferenciando ambos textos |

El contenido del canje aparece separado visualmente de RF-26 en la extracción de
la Entrega 4; se asocia a ese ID por su posición y categoría. Para la documentación
académica, conviene renumerar el segundo RF-28 como RF-29 sin perder la trazabilidad.

## Reglas adoptadas para poder implementar

Estas decisiones completan aspectos que los documentos no parametrizan:

1. La asignación de puntos es administrativa y explícita. No se inventa una tasa
   automática por quetzal o por servicio. Se exige una cita completada y un motivo.
2. La promoción define puntos_costo y sus condiciones. El canje registra el beneficio
   para entrega en el salón. Los descuentos publicados no se aplican automáticamente
   al checkout; no hay todavía relación de promoción con pedido en el modelo.
3. El checkout permite efectivo o tarjeta_simulada, con cuatro dígitos ficticios.
   Ninguna operación realiza un cobro, emite factura fiscal ni confirma una entrega.
   El estado completado significa pedido de demostración registrado.
4. Modificar o desactivar un horario no puede dejar citas pendientes/confirmadas
   futuras sin cobertura. Hay que resolver esas citas antes del cambio.
5. Desactivar una cuenta revoca sus tokens; reactivarla requiere iniciar sesión nuevamente. Conserva sus citas. El administrador puede cancelarlas
   incluso si el cliente/profesional está inactivo. No se cancelan automáticamente.
6. Cambiar un rol revoca sesiones y solo se permite cuando no existe historial
   ligado a ese rol. El administrador no puede cambiar su propio rol ni desactivarse.
7. La disponibilidad pública no filtra las otras citas del cliente: la creación y
   reprogramación sí verifican conflictos tanto del profesional como del cliente.
8. El precio vigente lo determina el servidor al confirmar un pedido. Cada línea
   conserva precio_unitario. La cantidad de stock solo cambia mediante movimientos,
   compras o reintegros de cancelación.

## Lo que no debe declararse terminado

- APK Android nativo, publicación en tiendas y comprobación en teléfono físico.
- Envíos de WhatsApp, SMS, correo o push. /recordatorios es una consulta interna;
  no existe un trabajador de entrega externa ni credenciales de proveedor.
- Pagos reales, reseñas, membresías Premium, factura fiscal y pasarela externa.
- TLS/HTTPS desplegado, pipeline Jenkins/Azure, restauración de respaldo y operación
  de ocho horas. Son entregables de infraestructura y aceptación, no logros demostrados
  por generar código.
- Rendimiento garantizado en el equipo del salón. La prueba de concurrencia local
  no acredita por sí sola RR-01 a RR-05 ni un SLA de producción.
- Múltiples servicios por cita, especialidades, vacaciones, feriados, cambio de
  profesional en una cita o auditoría completa de reprogramaciones.

## Siguiente secuencia de trabajo

La prioridad actual es aceptar el backend. El visor incluido es un prototipo opcional;
el website definitivo y la aplicación móvil se desarrollan después. Consultar
CIERRE_API.md e INTEGRACION_CLIENTES.md para la separación de entregables.


1. Instalar este paquete con Flask detenido, crear las tablas nuevas y comprobar
   la instalación con verificar_entrega.py.
2. Abrir el visor en PC y móvil; ejecutar el recorrido de aceptación de GUIA_VISOR.md.
3. Registrar defectos de interfaz y ajustar textos/estilos con el equipo.
4. Construir el cliente Android nativo usando openapi.json, sin duplicar reglas de
   negocio ni conectarse directamente a MySQL.
5. Actualizar el DER/diccionario y los diagramas UML con CAMBIOS_MODELO.md y esta
   arquitectura; preparar evidencias y manual del usuario a partir de pantallas reales.
6. Preparar despliegue HTTPS y respaldo cuando se elija el ambiente de publicación.
