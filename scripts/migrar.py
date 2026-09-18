"""Migración aditiva. No usa ni imprime la contraseña de .env."""
import argparse,getpass,os,sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine,text,inspect
from sqlalchemy.engine import URL

ROOT=Path(__file__).resolve().parent.parent
EXPECTED={
'productos':{'id','nombre','descripcion','categoria','tipo','precio','stock','imagen','activo'},
'promociones':{'id','titulo','descripcion','descuento_porcentaje','fecha_inicio','fecha_fin','activa','puntos_costo'},
'pedidos':{'id','usuario_id','fecha','total','estado','nombre_entrega','telefono_entrega','direccion_entrega','metodo_pago','tarjeta_ultimos4','clave_operacion','solicitud_hash'},
'pedido_detalle':{'id','pedido_id','producto_id','cantidad','precio_unitario'},
'movimientos_inventario':{'id','producto_id','usuario_id','tipo','cantidad','motivo','fecha'},
'puntos_historial':{'id','usuario_id','puntos','motivo','fecha','cita_id','promocion_id','clave_operacion'},
'tokens_revocados':{'jti','expira'},'sesiones_usuario':{'usuario_id','version'}}

def main():
    parser=argparse.ArgumentParser(description='Crea únicamente las tablas nuevas, sin borrar datos.')
    parser.add_argument('--verificar',action='store_true');args=parser.parse_args()
    load_dotenv(ROOT/'.env')
    database=os.getenv('DB_NAME');host=os.getenv('DB_HOST','localhost')
    if not database:raise RuntimeError('DB_NAME no está configurado.')
    print(f'Destino: {host}:{os.getenv("DB_PORT","3306")} / {database}')
    usuario=os.getenv('DB_USER') if args.verificar else input('Usuario MySQL con permiso CREATE (por ejemplo root): ').strip()
    password=os.getenv('DB_PASSWORD') if args.verificar else getpass.getpass('Contraseña MySQL: ')
    options={'connect_timeout':5}
    if os.getenv('DB_SSL_CA'):options.update(ssl_ca=os.environ['DB_SSL_CA'],ssl_verify_cert=True,ssl_verify_identity=True)
    motor=create_engine(URL.create('mysql+pymysql',username=usuario,password=password,host=host,port=int(os.getenv('DB_PORT','3306')),database=database,query={'charset':'utf8mb4'}),connect_args=options)
    try:
        schema=inspect(motor);tables=set(schema.get_table_names())
        if not {'usuarios','servicios','disponibilidades','citas'}<=tables:raise RuntimeError('Faltan tablas base; este paquete actualiza el proyecto existente.')
        if 'duracion_min' not in {c['name'] for c in schema.get_columns('citas')}:raise RuntimeError('La tabla citas no coincide con la versión revisada.')
        for table,columns in EXPECTED.items():
            if table in tables and {c['name'] for c in schema.get_columns(table)}!=columns:
                raise RuntimeError(f'La tabla {table} existe con otras columnas. Se requiere revisión; no se modificó.')
        missing=set(EXPECTED)-tables
        if args.verificar:
            if missing:raise RuntimeError('Tablas pendientes: '+', '.join(sorted(missing)))
            print('Esquema presente. Ejecuta después las pruebas funcionales.');return
        sql='\n'.join(l for l in (ROOT/'database/005_completar_api.sql').read_text(encoding='utf-8').splitlines() if not l.strip().startswith('--'))
        with motor.connect() as c:
            for statement in sql.split(';'):
                if statement.strip():c.execute(text(statement));c.commit()
        print('Tablas nuevas disponibles. Las tablas y datos anteriores se conservaron.')
        print('MySQL confirma DDL por sentencia. Si se interrumpe, se puede volver a ejecutar.')
    finally:motor.dispose()

if __name__=='__main__':
    try:main()
    except Exception as e:
        # No imprimir errores DBAPI con parámetros de conexión.
        from sqlalchemy.exc import SQLAlchemyError
        print('ERROR: '+('No fue posible completar la migración. Revisa conexión y permisos CREATE.' if isinstance(e,SQLAlchemyError) else str(e)),file=sys.stderr)
        sys.exit(1)
