# Seguimiento de la versión 1.1

## Base del trabajo

BellezaIntegral(1).zip, suministrado después de aplicar el primer parche de
administración de usuarios. No se parte del ZIP anterior.

## Evidencia previa del usuario

- Rutas del parche administrativo cargadas sin error.
- Consulta administrativa de usuarios contra MySQL.
- Personal nuevo ID 7 creado por API.
- Inicio de sesión de esa cuenta, desactivación, rechazo 401 del token mientras la
  cuenta estaba inactiva y reactivación a activo true.
- Cita ID 2 del cliente 1, profesional 4, 2026-09-14 a las 11:00, confirmada en la
  última consulta mostrada. Son datos históricos de prueba, no valores a imponer.

## Entregado ahora

- Código de cierre funcional de API y visor responsivo.
- Migración aditiva de seis tablas de negocio y dos técnicas.
- OpenAPI válido y colección Postman de 62 operaciones.
- Scripts de aplicación/restauración, instalación, ejecución y verificación local.
- Suite MySQL aislada con doce pruebas; prueba de DOM contra backend real.
- Matriz de entregables/requisitos y ajustes al modelo académico.

## Pendiente para dar por instalada esta versión

1. Ejecutar INSTALAR.cmd con Flask detenido.
2. Ejecutar scripts/verificar_entrega.py con una cuenta administradora existente.
3. Abrir el visor en PC y teléfono; hacer el recorrido de GUIA_VISOR.md.
4. Registrar resultados locales y defectos de interfaz antes de capturas finales.

## Continuidad

Después de esa aceptación, el siguiente desarrollo es el cliente Android nativo y
el ajuste visual de web. No volver a implementar autenticación, reglas de citas,
stock ni puntos en el frontend. El contrato está en docs/openapi.json.

Quedan como trabajo de infraestructura/integración: HTTPS, backups/restauración,
CI/CD, mensajería externa y pruebas de operación prolongada. Pagos reales y reseñas
no se presentan como implementados. El checkout actual es una demostración.


## Revisión 1.1.1 sobre BellezaIntegral(2).zip

La nueva carga todavía corresponde a la base previa a 1.1; coincide con los hashes
normalizados de esa base. Se recuperó el paquete anterior y se mantuvieron sus módulos.
Se corrigió la reactivación de tokens antiguos y se unificó en una transacción la
validación de contraseña y lectura de versión de sesión. Se amplió el verificador
local para producir evidencia de aceptación tanto en éxito como en fallo.
Website definitivo y Android continúan después de aceptar las APIs. Consultar
CIERRE_API.md e INTEGRACION_CLIENTES.md. No se presupone que la instalación local
haya pasado hasta recibir el resultado de VERIFICAR.cmd.
