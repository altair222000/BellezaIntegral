# Cierre de APIs y definición de entregables — Belleza Integral 1.1.1

## Estado concreto

El ZIP BellezaIntegral(2).zip coincide, en los módulos base revisados, con la versión
sobre la que se preparó el cierre anterior. Todavía no contiene aquella ampliación.
Este paquete acumula la ampliación y las correcciones de cierre; se instala una sola
vez sobre el ZIP recibido. También admite la versión 1.1 anterior sin ediciones locales.

Se entregan 62 operaciones REST con contrato OpenAPI. Se verificaron 15 pruebas de
integración en MySQL aislado. Esto permite iniciar el desarrollo de clientes contra
un contrato definido. La aceptación de la instalación Windows está pendiente hasta
que el verificador se ejecute allí. No se declara un sistema ya desplegado.

## Entregables de backend

| ID | Archivo o componente entregado | Criterio para aceptarlo | Evidencia actual |
|---|---|---|---|
| API-01 Cuentas y seguridad | app/auth*, cuentas_routes.py, security.py y módulos administrativos | Registro cliente, login, perfil, roles; ningún acceso con token cerrado, cuenta desactivada o token previo a reactivación | Pruebas de sesiones, roles y desactivación |
| API-02 Agenda | servicios, personal, disponibilidad, citas, agenda y horarios | Reservar, confirmar, reprogramar, cancelar y completar respetando propiedad, tiempo y conflictos | Pruebas funcionales y dos reservas concurrentes |
| API-03 Inventario y tienda | tienda_routes.py | Existencias auditables, precios calculados por servidor y pedido sin duplicación | Pruebas de stock, reversión y dos compras concurrentes |
| API-04 Fidelización | fidelizacion_routes.py | Asignar una vez por cita completada y canjear sin saldo negativo ni doble descuento | Prueba de asignación, canje e idempotencia |
| API-05 Reportes | reportes_routes.py | Consulta por período y XLSX legible, solo administrador | Prueba de reporte/exportación |
| API-06 Persistencia | database/005_completar_api.sql y scripts/migrar.py | Crear tablas nuevas sin borrar las existentes; verificar permisos de cuenta de aplicación | Migración utilizada por la suite; ejecución local pendiente |
| API-07 Contrato | openapi.json, RUTAS.md, postman_collection.json | Todas las operaciones registradas coinciden con OpenAPI; no exponer rutas protegidas sin token | Contrato validado y prueba de aceptación |
| API-08 Instalación y aceptación | actualizar_api.py, INSTALAR.cmd, VERIFICAR.cmd | Respaldo, aplicación repetible y restauración; resultado local aprobado | Pruebas del instalador; aceptación Windows pendiente |
| API-09 Continuidad | ENTREGABLES.md, CAMBIOS_MODELO.md, INTEGRACION_CLIENTES.md | Requisitos, decisiones y próximos entregables identificables | Documentación incluida |

## Definición de terminado del backend

El código queda entregado cuando compila, pasa la suite de integración, el contrato
es válido y el instalador es reproducible. La instalación del equipo queda aceptada
cuando se cumplen estos puntos:

1. INSTALAR.cmd termina sin error y el esquema nuevo se verifica con la cuenta de aplicación.
2. VERIFICAR.cmd termina con código 0 y docs/RESULTADO_LOCAL.json contiene aprobado: true.
3. INICIAR_PC.cmd permite consultar /api/v1/health/db por HTTP en el equipo.
4. El responsable del proyecto conserva el resultado local y la versión 1.1.1 con sus evidencias.

El verificador usa Flask test_client y la base configurada. No reemplaza la prueba
del servidor HTTP del punto 3. No crea citas, usuarios, pedidos ni movimientos; sí
crea y revoca una sesión. Las pruebas de escritura se ejecutan en una BD aislada.

## Entregables siguientes, en orden

| Fase | Entregable | Criterio de aceptación |
|---|---|---|
| WEB-01 | Website: estructura y navegación por rol | Prototipos aprobados y correspondencia pantalla/operación de API |
| WEB-02 | Website: cliente | Registro, sesión, catálogo, reserva, mis citas, reprogramación, cancelación, pedidos y puntos con errores visibles |
| WEB-03 | Website: personal y administración | Agenda propia; gestión de usuarios, servicios, horarios, inventario, promociones y reportes |
| WEB-04 | Website: aceptación | Pruebas en escritorio/teléfono, teclado, estados vacíos, carga y errores; sin credenciales de MySQL en frontend |
| MOV-01 | Aplicación Android: proyecto y cliente HTTP | Compila y consume la misma API mediante URL configurable |
| MOV-02 | Aplicación Android: flujos del cliente | Login, catálogo, disponibilidad, citas, pedidos y puntos, con expiración de sesión y reintentos controlados |
| MOV-03 | APK y manual | APK instalado y probado en dispositivo; evidencia de los recorridos acordados |
| OPS-01 | Ambiente de publicación | HTTPS, secretos, respaldos/restauración, logs y prueba de carga sobre el ambiente elegido |

El visor de la entrega anterior se conserva como herramienta opcional para probar
la API. No equivale al website definitivo ni a una aplicación móvil nativa.

## Alcance y decisiones que deben constar en la entrega académica

- Referencia funcional: Entrega 4 y Entrega 7.1 revisada; trazabilidad completa en ENTREGABLES.md.
- Se adopta REST compartida por website y móvil por la instrucción del proyecto.
  Debe corregirse la descripción Jinja2 sin REST de la Entrega 7.
- Pagos: simulación según la Entrega 7. No se integra una pasarela ni se cobra dinero.
- Recordatorios: consulta interna de próximas citas, sin envíos externos.
- Reseñas: backlog de baja prioridad de Sprint 0, fuera del cierre funcional RF-01 a RF-28.
- Promociones: beneficios y canje registrado; no descuento automático sobre pedidos.
- Diagramas: incorporar los cambios de CAMBIOS_MODELO.md; la generación de esta
  matriz no significa que los diagramas originales ya hayan sido editados.
- No se acreditan todavía producción, tiempos de respuesta del salón, operación
  continua de ocho horas ni publicación de website/APK.

No hace falta agregar más pantallas para aceptar el backend. Primero registrar la
aceptación local; después continuar con WEB-01 sobre el contrato entregado.
