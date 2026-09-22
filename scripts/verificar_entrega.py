"""Aceptación local de API. No crea ni cambia registros del negocio."""
import getpass
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def verificar(app, identificador, password, destino=None):
    client = app.test_client()
    resultados = []
    headers = None
    contrato = {}

    def registrar(nombre, correcto, http=None):
        fila = {'comprobacion': nombre, 'correcto': bool(correcto)}
        if http is not None:
            fila['http'] = http
        resultados.append(fila)
        print(('OK ' if correcto else 'ERROR ') + nombre)

    def consultar(ruta, cabeceras=None):
        r = client.get(ruta, headers=cabeceras or {})
        d = r.get_json(silent=True)
        registrar('GET ' + ruta, r.status_code == 200 and isinstance(d, dict)
                  and d.get('success') is True, r.status_code)

    try:
        r = client.get('/api/v1/openapi.json')
        contrato = r.get_json(silent=True) or {}
        rutas = contrato.get('paths', {})
        documentadas = {(p, m.upper()) for p, ops in rutas.items()
                        for m in ops if m in ('get', 'post', 'put', 'patch', 'delete')}
        reales = {(re.sub(r'<(?:[^:>]+:)?([^>]+)>', r'{\1}', regla.rule), m)
                  for regla in app.url_map.iter_rules()
                  if regla.rule.startswith('/api/v1/') and regla.rule != '/api/v1/openapi.json'
                  for m in regla.methods - {'HEAD', 'OPTIONS'}}
        coincide = r.status_code == 200 and bool(documentadas) and documentadas == reales
        registrar('Contrato coincide con todas las operaciones de Flask', coincide, r.status_code)
        if not coincide:
            solo_flask = sorted(reales - documentadas)
            solo_contrato = sorted(documentadas - reales)
            if solo_flask:
                print('  Solo Flask: ' + ', '.join(f'{m} {p}' for p, m in solo_flask))
            if solo_contrato:
                print('  Solo contrato: ' + ', '.join(f'{m} {p}' for p, m in solo_contrato))
        # Solo rutas protegidas: las solicitudes sin token deben rechazarse antes
        # de procesar cuerpo o tocar registros. No usar credenciales en esta fase.
        for ruta, ops in rutas.items():
            for metodo, op in ops.items():
                if metodo not in ('get', 'post', 'put', 'patch', 'delete'):
                    continue
                if not op.get('security', contrato.get('security', [])):
                    continue
                url = re.sub(r'\{[^}]+\}', '1', ruta)
                r = client.open(url, method=metodo.upper())
                d = r.get_json(silent=True)
                registrar('Sin sesión: ' + metodo.upper() + ' ' + ruta,
                          r.status_code == 401 and isinstance(d, dict) and d.get('success') is False,
                          r.status_code)
        for ruta in ('/health', '/health/db', '/servicios', '/productos', '/promociones', '/personal'):
            consultar('/api/v1' + ruta)
        r = client.post('/api/v1/auth/login', json={'identificador': identificador, 'password': password})
        d = r.get_json(silent=True) or {}
        token = (d.get('data') or {}).get('access_token')
        registrar('Login de comprobación', r.status_code == 200 and bool(token), r.status_code)
        if token:
            headers = {'Authorization': 'Bearer ' + token}
            admin = (d.get('data') or {}).get('usuario', {}).get('rol') == 'administrador'
            registrar('Cuenta de comprobación administradora', admin)
            if admin:
                for ruta in ('usuarios', 'citas', 'servicios', 'productos', 'inventario/movimientos',
                             'pedidos', 'promociones', 'puntos/historial', 'reportes/resumen'):
                    consultar('/api/v1/admin/' + ruta, headers)
                r = client.get('/api/v1/admin/reportes/citas.xlsx', headers=headers)
                from io import BytesIO
                from openpyxl import load_workbook
                valido = False
                if r.status_code == 200:
                    try:
                        libro = load_workbook(BytesIO(r.data), read_only=True)
                        valido = libro.active['A1'].value == 'id'
                        libro.close()
                    except Exception:
                        pass
                registrar('Exportación XLSX legible', valido, r.status_code)
    except Exception:
        # Nunca volcar excepciones que puedan incluir parámetros o datos privados.
        registrar('Ejecución completa (revisar configuración, migración y permisos)', False)
    finally:
        if headers:
            try:
                r = client.post('/api/v1/auth/logout', headers=headers)
                registrar('Cierre de sesión', r.status_code == 200, r.status_code)
                r = client.get('/api/v1/auth/perfil', headers=headers)
                registrar('Token cerrado ya no permite acceso', r.status_code == 401, r.status_code)
            except Exception:
                registrar('Cierre de sesión verificable', False)
        informe = {'version': contrato.get('info', {}).get('version', 'desconocida'), 'fecha_utc': datetime.now(timezone.utc).isoformat(),
                   'aprobado': bool(resultados) and all(x['correcto'] for x in resultados),
                   'comprobaciones': resultados,
                   'alcance': 'Flask test_client sobre la BD configurada; no verifica TCP, HTTPS ni interfaces. '
                              'No modifica datos del negocio; abre y revoca una sesión.'}
        destino = Path(destino or ROOT / 'docs/RESULTADO_LOCAL.json')
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if informe['aprobado'] else 1


def main():
    from app import create_app
    app = create_app()
    identificador = input('Correo o teléfono del administrador de la aplicación: ').strip()
    password = getpass.getpass('Contraseña (no se guarda): ')
    resultado = verificar(app, identificador, password)
    print('Informe: docs/RESULTADO_LOCAL.json')
    return resultado


if __name__ == '__main__':
    sys.exit(main())
