import json
from sqlalchemy import text
from test_flujos import call


def test_desactivar_reactivar_no_rehabilita_token(client, headers, motor):
    sesion=call(client,headers,'/auth/login','POST',{'identificador':'cuenta2@example.com','password':'PasswordTest2026!'})
    h={'Authorization':'Bearer '+sesion['data']['access_token']}
    call(client,headers,'/admin/usuarios/2/estado','PATCH',{'activo':False})
    assert client.get('/api/v1/auth/perfil',headers=h).status_code==401
    call(client,headers,'/admin/usuarios/2/estado','PATCH',{'activo':False})
    with motor.connect() as c:
        assert c.execute(text('SELECT version FROM sesiones_usuario WHERE usuario_id=2')).scalar_one()==1
    call(client,headers,'/admin/usuarios/2/estado','PATCH',{'activo':True})
    assert client.get('/api/v1/auth/perfil',headers=h).status_code==401
    nueva=call(client,headers,'/auth/login','POST',{'identificador':'cuenta2@example.com','password':'PasswordTest2026!'})
    assert '_version_sesion' not in nueva['data']['usuario']
    assert client.get('/api/v1/auth/perfil',headers={'Authorization':'Bearer '+nueva['data']['access_token']}).status_code==200


def test_contrato_y_aceptacion_local(app, tmp_path):
    from openapi_spec_validator import validate
    from pathlib import Path
    contrato=json.loads((Path(__file__).parents[1]/'docs/openapi.json').read_text())
    validate(contrato)
    from scripts.verificar_entrega import verificar
    out=tmp_path/'resultado.json'
    assert verificar(app,'cuenta1@example.com','PasswordTest2026!',out)==0
    informe=json.loads(out.read_text())
    assert informe['aprobado']
    assert len(informe['comprobaciones'])>60
    assert 'PasswordTest2026!' not in out.read_text()
    assert 'access_token' not in out.read_text()


def test_aceptacion_fallida_guarda_resultado(app, tmp_path):
    from scripts.verificar_entrega import verificar
    out=tmp_path/'fallo.json'
    assert verificar(app,'cuenta1@example.com','incorrecta',out)==1
    assert json.loads(out.read_text())['aprobado'] is False
