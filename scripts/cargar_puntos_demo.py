"""Carga autorizada de prueba, separada de los puntos por atención real."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
EMAIL='cliente.dos@example.com'
KEY='cierre_web_demo_100_cliente_dos_v1'
MOTIVO='Carga de prueba autorizada: 100 puntos para validar canje'

def cargar(motor):
    from sqlalchemy import text
    with motor.begin() as c:
        rows=c.execute(text('SELECT id,rol,activo,puntos FROM usuarios WHERE email=:email FOR UPDATE'),{'email':EMAIL}).mappings().all()
        if len(rows)!=1:raise ValueError('Se requiere exactamente un cliente con correo '+EMAIL)
        u=rows[0]
        if u['rol']!='cliente' or not u['activo']:raise ValueError('La cuenta debe ser cliente y estar activa.')
        old=c.execute(text('SELECT id,puntos,motivo FROM puntos_historial WHERE usuario_id=:u AND clave_operacion=:k'),{'u':u['id'],'k':KEY}).mappings().first()
        if old:
            if old['puntos']!=100 or old['motivo']!=MOTIVO:raise ValueError('La referencia existe con otro contenido; no se modificó el saldo.')
            return {'email':EMAIL,'agregados':0,'saldo':u['puntos'],'referencia':old['id'],'mensaje':'Carga ya aplicada; no se repite aunque hayas canjeado puntos.'}
        if u['puntos']+100>4294967295:raise ValueError('Saldo fuera de rango.')
        from app.db_context import cambio_puntos_controlado
        with cambio_puntos_controlado(c):
            id=c.execute(text('INSERT INTO puntos_historial(usuario_id,puntos,motivo,clave_operacion) VALUES(:u,100,:m,:k)'),{'u':u['id'],'m':MOTIVO,'k':KEY}).lastrowid
            c.execute(text('UPDATE usuarios SET puntos=puntos+100 WHERE id=:u'),{'u':u['id']})
        return {'email':EMAIL,'agregados':100,'saldo':u['puntos']+100,'referencia':id,'mensaje':'Carga de prueba registrada; no representa una cita completada.'}

if __name__=='__main__':
    try:
        from app import create_app
        app=create_app();result=cargar(app.extensions['db_engine']);print(json.dumps(result,ensure_ascii=False,indent=2))
        try:
            (ROOT/'docs/RESULTADO_PUNTOS_DEMO.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        except OSError:print('La carga se confirmó en MySQL; no se pudo escribir el informe local.')
    except Exception as exc:
        # Los errores de conexión pueden incluir información del motor; no imprimir credenciales.
        print('ERROR: '+(str(exc) if isinstance(exc,ValueError) else 'No se completó la carga. Revisa MySQL, .env y las tablas del proyecto.'))
        sys.exit(1)
