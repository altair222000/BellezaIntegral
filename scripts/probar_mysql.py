"""Ejecuta la suite únicamente en una base aislada de pruebas."""
import getpass,os,subprocess,sys
from pathlib import Path
from sqlalchemy.engine import URL
ROOT=Path(__file__).resolve().parent.parent
if __name__=='__main__':
    name=input('Nombre de base VACÍA terminada en _test: ').strip()
    if not name.endswith('_test'):raise SystemExit('Se rechazó el nombre de base de datos.')
    host=input('Servidor MySQL [127.0.0.1]: ').strip() or '127.0.0.1'
    port=int(input('Puerto [3306]: ').strip() or '3306')
    user=input('Usuario autorizado SOLO para esa base de pruebas: ').strip()
    password=getpass.getpass('Contraseña: ')
    url=URL.create('mysql+pymysql',username=user,password=password,host=host,port=port,database=name)
    env={**os.environ,'BELLEZA_TEST_DATABASE_URL':url.render_as_string(hide_password=False)}
    result=subprocess.run([sys.executable,'-m','pytest','tests','-q'],cwd=ROOT,env=env)
    sys.exit(result.returncode)
