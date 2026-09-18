"""Comprueba vistas y contratos locales sin modificar registros de negocio."""
import sys,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))

def main():
    from app import create_app
    app=create_app();client=app.test_client();rows=[]
    def check(name,ok):
        rows.append({'prueba':name,'correcto':bool(ok)});print(('OK ' if ok else 'ERROR ')+name)
    js=(ROOT/'app/web/app.js').read_text(encoding='utf-8-sig')
    names={a or b for a,b in re.findall(r'''screens(?:\[['"]([^'"]+)['"]\]|\.(\w+))\s*=''',js)}
    expected={'Inicio','Servicios','Ingresar','Registrarme','Mi cuenta','Mis citas','Mi agenda','Productos','Carrito','Mis pedidos','Promociones','Mis puntos','Usuarios','Servicios admin','Horarios','Inventario','Pedidos admin','Promociones admin','Puntos admin','Reportes','Citas admin','Recordatorios','Clientes','Movimientos de inventario'}
    check('Registro de las 24 pantallas',expected<=names)
    for path in ['/','/api/v1/health','/api/v1/health/db','/api/v1/productos','/api/v1/promociones']:
        r=client.get(path);check('GET '+path,r.status_code==200)
    for path in ['/api/v1/recordatorios','/api/v1/admin/clientes','/api/v1/admin/inventario/movimientos','/api/v1/puntos']:
        check('Protección sin sesión '+path,client.get(path).status_code==401)
    from sqlalchemy import text
    with app.extensions['db_engine'].connect() as c:
        r=c.execute(text('SELECT h.puntos FROM puntos_historial h JOIN usuarios u ON u.id=h.usuario_id WHERE u.email=:e AND h.clave_operacion=:k'),{'e':'cliente.dos@example.com','k':'cierre_web_demo_100_cliente_dos_v1'}).all()
        check('Carga de prueba única de 100 puntos',len(r)==1 and r[0][0]==100)
    (ROOT/'docs/RESULTADO_CIERRE_WEB.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if all(r['correcto'] for r in rows) else 1
if __name__=='__main__':
    try:sys.exit(main())
    except Exception:print('ERROR: verificación incompleta. Revisa configuración y disponibilidad de MySQL.');sys.exit(1)
