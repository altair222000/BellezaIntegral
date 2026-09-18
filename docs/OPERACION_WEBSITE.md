# Operación e integración antes de APK

## Instalación
Detener Flask con Ctrl+C. Extraer el ZIP. Ejecutar INSTALAR_CIERRE_WEB.cmd.
El script usa C:/Proyectos/BellezaIntegral/api; se puede pasar otra ruta como argumento.
Instala los archivos, crea respaldo, carga puntos y verifica. Si falla MySQL,
corregir la configuración y volver a ejecutar: la carga no se duplica.
Los pasos de archivos y base de datos son separados; un error de verificación
no deshace una carga de puntos ya confirmada. Consultar el mensaje y el historial.
Reiniciar con INICIAR_PC.cmd habitual y Ctrl+F5. No se instalan dependencias nuevas.

## Informes
- docs/RESULTADO_PUNTOS_DEMO.json: resultado de la bonificación.
- docs/RESULTADO_CIERRE_WEB.json: chequeos automáticos básicos.
- scripts/verificar_entrega.py: aceptación existente con credenciales del administrador,
  solicitadas en consola. Ejecutar VERIFICAR_ADMIN.cmd del paquete; no guarda contraseña.
Los chequeos básicos no sustituyen los flujos por rol de la matriz de aceptación.

## Recuperación
El instalador muestra comando --restaurar con el respaldo específico. Restaura archivos
si no hay modificaciones posteriores. No revierte puntos ni operaciones de MySQL.
La bonificación conserva su referencia auditable; no borrar movimientos para ocultarla.
Para respaldo completo, usar el procedimiento de exportación MySQL de la instalación
antes de futuras migraciones; este paquete no cambia tablas ni borra datos.
Guardar una copia del proyecto actualizado, excluyendo .venv y cachés. Proteger .env
como configuración privada; no incluirlo en repositorios o entregas académicas públicas.

## Pruebas desde teléfono / siguiente APK
Ejecutar INICIAR_LAN.cmd (detener primero otro servidor en el puerto 5000).
Consultar IPv4 del PC con ipconfig y abrir http://IP_DEL_PC:5000 desde el teléfono
en la misma red. Si Windows solicita acceso, limitarlo a red privada.
127.0.0.1 en el teléfono se refiere al teléfono, no al PC.
Para acceso por Internet habrá que definir alojamiento y HTTPS. No abrir el puerto
del router para esta prueba local. La APK será una entrega posterior contra la misma
API /api/v1; falta construirla y validar instalación, sesión y flujos en Android.

## Manual breve por rol
Cliente: catálogo → reservar → Mis citas; Productos → Carrito → Mis pedidos;
Promociones → confirmar canje → Mis puntos; Recordatorios → próximas citas.
Personal: Mi agenda → consultar fecha → confirmar/completar; Recordatorios.
Administrador: Usuarios/Clientes; servicios/horarios/citas; inventario/movimientos;
pedidos y cancelaciones; promociones; asignación de puntos; reportes y XLSX.
