# Visor web y acceso desde móvil

## En el PC

Después de instalar el paquete, ejecuta desde api:

```powershell
.\.venv\Scripts\python.exe .\scripts\servir.py
```

Abre http://127.0.0.1:5000/ en el navegador. La pantalla inicial es el catálogo;
la API sigue disponible bajo /api/v1. El visor no necesita npm ni un servidor web
separado. Usa las cuentas existentes, incluidas las que ya se probaron en PowerShell.

Al recargar la página se solicita iniciar sesión otra vez: el visor guarda el token
solo en memoria. Salir revoca el token en el servidor. El cambio de contraseña y
el cambio de rol invalidan todas las sesiones anteriores del usuario.

## En el teléfono

1. PC y teléfono deben estar en la misma red privada.
2. Detén el servidor anterior con Ctrl+C y ejecuta:

```powershell
.\.venv\Scripts\python.exe .\scripts\servir.py --lan
```

3. Ejecuta `ipconfig` e identifica la dirección IPv4 del adaptador conectado a esa red.
4. En el teléfono abre `http://IP_DEL_PC:5000/`, sustituyendo IP_DEL_PC por esa IPv4.
   No uses 127.0.0.1 ni 0.0.0.0 en el teléfono: no identifican al PC remoto.
5. Si Windows solicita permiso, permite Python únicamente en tu red privada de pruebas.
   No es necesario abrir MySQL al teléfono ni configurar un reenvío del router.

Esta modalidad usa HTTP para pruebas locales con cuentas ficticias. Para uso real
se requiere HTTPS con un certificado válido. El script no cambia el firewall ni
publica el sistema en Internet.

## Recorrido de aceptación

| Rol | Recorrido | Qué comprobar |
|---|---|---|
| Visitante | Servicios, productos, promociones, registrarme | Catálogo legible y registro correcto |
| Cliente | Ingresar, reservar, mis citas, reprogramar, cancelar | Mensajes claros, fechas y disponibilidad coherentes |
| Cliente | Productos, carrito, pedido, mis pedidos | Pedido de demostración y cantidades correctas |
| Cliente | Mis puntos, promociones, canjear | Saldo e historial coherentes |
| Personal | Mi agenda, confirmar, completar | Solo citas propias; no completar antes del final |
| Administrador | Usuarios y servicios | Crear, editar y cambiar estado con validaciones |
| Administrador | Horarios | Bloques sin solapamiento ni citas desprotegidas |
| Administrador | Inventario y pedidos | Movimientos con motivo y reintegros de cancelación |
| Administrador | Promociones y puntos | Beneficios vigentes y asignación por cita completada |
| Administrador | Reportes | Período y descarga de Excel |

Comprueba a 390 px aproximadamente, en orientación vertical y horizontal, que los
formularios sean accesibles, que el menú permita desplazamiento y que las tablas
se desplacen dentro de su contenedor. Registra navegador, dispositivo, pasos y
captura cuando aparezca un problema. No se han verificado visualmente dispositivos
reales desde este entorno.

## Conectar una interfaz separada o Android nativo

- Base URL de la API: https://TU_DOMINIO/api/v1 en el ambiente publicado.
- Authorization: Bearer TOKEN en solicitudes protegidas.
- Content-Type: application/json para cuerpos JSON.
- Fechas YYYY-MM-DD y horas HH:MM en America/Guatemala.
- Precios como texto decimal; la interfaz no determina totales ni permisos.
- HTTP 401: limpiar sesión y solicitar login. HTTP 403: rol sin permiso.
- HTTP 404 puede indicar recurso ajeno. No intentes revelar su propietario.
- HTTP 409: mostrar el conflicto y actualizar datos/disponibilidad.
- Pedidos y canjes: conservar clave_operacion para reintentar la misma operación.
- Solo para frontend web de origen distinto: configurar CORS_ORIGINS con orígenes
  exactos. CORS no reemplaza JWT ni el control por roles.
- Una app Android nativa debe guardar el token en almacenamiento apropiado para
  credenciales de la plataforma y descartar el token al salir. No conectar a MySQL.
- En emulador/dispositivo, definir la base URL según su conectividad al PC. Para
  pruebas con teléfono físico usa la IPv4 de LAN como se explicó arriba.

El visor responsivo está incluido. Una app Android nativa y su APK son otra entrega:
se puede desarrollar ahora usando docs/openapi.json sin esperar más rutas básicas.

Referencia para el servidor Windows:
[Flask y Waitress](https://flask.palletsprojects.com/en/stable/deploying/waitress/).
