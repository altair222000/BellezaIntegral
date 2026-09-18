# Verificación de la entrega

## Pruebas ejecutadas por esta entrega

Entorno aislado: Python 3.12, Flask 3.1, SQLAlchemy 2 y MySQL Community 8.4.11.
No se accedió a la base del usuario ni se ejecutó el instalador en su Windows.

Quince pruebas de integración pasaron en la revisión 1.1.1:

1. Login/logout, perfil, cambio de contraseña, invalidación de tokens y roles.
2. Accesos no autorizados, validación, duplicados MySQL, CORS, 405 y tamaño máximo.
3. Citas, horarios, reprogramación, propietario y estados permitidos.
4. Pedido, precio del servidor, idempotencia, stock y cancelación con reintegro.
5. Puntos: cita completada, asignación única, beneficio vigente y saldo suficiente.
6. Reportes y archivo XLSX que puede abrirse con openpyxl.
7. Dos reservas simultáneas: una respuesta 201 y una 409.
8. Dos compras simultáneas de la última unidad: una 201 y una 409; stock final cero.
9. Reprogramación hacia un intervalo ocupado: 409 y conservación de la hora original.
10. Gestión administrativa del estado de citas, incluida cuenta desactivada.
11. Compra con dos productos y stock insuficiente: sin persistencia parcial.
12. Veinte consultas simultáneas de disponibilidad: respuestas 200.
13. Desactivar/reactivar no rehabilita tokens; nueva sesión válida y desactivación repetida idempotente.
14. OpenAPI válido, todas las operaciones coinciden y verificador local aprobado con administrador.
15. El verificador conserva un resultado fallido cuando el login no es válido.

Las pruebas 7 y 8 usan conexiones concurrentes reales contra MySQL. La prueba 12
es una comprobación local corta; no demuestra el SLA ni ocho horas de operación.

Se validaron sintaxis Python y OpenAPI en la revisión 1.1.1. En la entrega 1.1 anterior se comprobó también JavaScript. Las pruebas de DOM anteriores
usan el JavaScript del visor y solicitudes HTTP al backend real: no son capturas
ni una medición de diseño adaptable. El navegador Chromium no pudo arrancar por
una restricción de sockets del entorno; la revisión visual en navegador y móvil
queda pendiente en el PC del usuario.

## Verificación no destructiva de la instalación actual

Desde api:

```powershell
.\.venv\Scripts\python.exe .\scripts\verificar_entrega.py
```

Solicita credenciales administrativas. Contrasta todas las operaciones con OpenAPI,
comprueba rutas protegidas sin token, consultas administrativas, XLSX y revocación.
Guarda indicadores y estados HTTP en docs/RESULTADO_LOCAL.json, incluso si falla el login. No crea usuarios, pedidos o citas;
crea y cierra una sesión de prueba. No registra contraseñas ni tokens en el informe.

## Repetir la suite de integración

La suite limpia sus tablas de prueba. Requiere una base VACÍA y aislada cuyo nombre
termine en _test. No acepta una base que ya tenga tablas sin su marcador de pruebas.
Nunca apuntar al esquema belleza_integral_dev ni a datos del salón.

1. Crear una base separada en MySQL y un usuario autorizado solo para esa base.
2. Instalar dependencias de prueba:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-test.txt
.\.venv\Scripts\python.exe .\scripts\probar_mysql.py
```

Se solicitan nombre, host, puerto, usuario y contraseña. La contraseña se transmite
al proceso de pruebas mediante su entorno, sin imprimirla ni escribirla a un archivo.
Sin BELLEZA_TEST_DATABASE_URL, pytest omite las pruebas MySQL: un resultado skipped
no debe presentarse como aprobado.

## Pruebas que siguen abiertas

- Windows/Python 3.13 y la instalación MySQL del usuario.
- Navegadores y dispositivos reales; teclado, accesibilidad y adaptación visual.
- Despliegue HTTPS, certificados MySQL, restauración de respaldo y operación de 8 h.
- Rendimiento del ambiente final y pruebas de aceptación con el negocio.
- Envío de notificaciones externas: no existe esa integración en esta versión.
