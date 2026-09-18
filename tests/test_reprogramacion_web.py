from sqlalchemy import text
from test_flujos import call,catalog


def test_horarios_privados_con_duracion_historica(client,headers,motor):
    s,date,block=catalog(client,headers)
    own=call(client,headers,'/citas','POST',{'personal_id':3,'servicio_id':s,'fecha':date,'hora':'09:00'},id=2,expected=201)['data']['id']
    from datetime import date as Date
    call(client,headers,'/personal/5/disponibilidades','POST',{'dia_semana':Date.fromisoformat(date).isoweekday(),'hora_inicio':'09:00','hora_fin':'17:00'},expected=201)
    call(client,headers,'/citas','POST',{'personal_id':5,'servicio_id':s,'fecha':date,'hora':'11:00'},id=2,expected=201)
    call(client,headers,'/citas','POST',{'personal_id':3,'servicio_id':s,'fecha':date,'hora':'14:00'},id=4,expected=201)
    with motor.begin() as c:c.execute(text('UPDATE servicios SET duracion_min=120 WHERE id=:id'),{'id':s})
    path=f'/citas/{own}/disponibilidad?fecha={date}'
    result=call(client,headers,path,id=2)['data'];hours={h['hora_inicio']:h['hora_fin'] for h in result['horarios']}
    assert result['duracion_min']==60
    assert hours['09:00']=='10:00'  # La cita actual no bloquea su propio intervalo.
    assert hours['13:00']=='14:00'  # Mantiene 60, no los 120 actuales del catálogo.
    assert '11:00' not in hours  # Otra cita del cliente con otro profesional.
    assert '14:00' not in hours  # Otra cita del profesional con otro cliente.
    assert client.get('/api/v1'+path).status_code==401
    call(client,headers,path,id=4,expected=404)
    call(client,headers,path,id=1,expected=403)
    call(client,headers,path+'&fecha='+date,id=2,expected=400)
    call(client,headers,path+'&cliente_id=4',id=2,expected=400)
    call(client,headers,f'/citas/{own}/reprogramar','PATCH',{'fecha':date,'hora':'13:00'},id=2)
    with motor.connect() as c:
        row=c.execute(text('SELECT estado,duracion_min FROM citas WHERE id=:id'),{'id':own}).mappings().one()
        assert row['estado']=='pendiente' and row['duracion_min']==60
    call(client,headers,f'/citas/{own}/cancelar','PATCH',id=2)
    call(client,headers,path,id=2,expected=409)


def test_consulta_no_reserva_y_conflicto_al_guardar(client,headers,motor):
    s,date,_=catalog(client,headers)
    own=call(client,headers,'/citas','POST',{'personal_id':3,'servicio_id':s,'fecha':date,'hora':'09:00'},id=2,expected=201)['data']['id']
    hours=call(client,headers,f'/citas/{own}/disponibilidad?fecha={date}',id=2)['data']['horarios']
    assert any(h['hora_inicio']=='13:00' for h in hours)
    call(client,headers,'/citas','POST',{'personal_id':3,'servicio_id':s,'fecha':date,'hora':'13:00'},id=4,expected=201)
    call(client,headers,f'/citas/{own}/reprogramar','PATCH',{'fecha':date,'hora':'13:00'},id=2,expected=409)
    with motor.connect() as c:assert c.execute(text("SELECT TIME_FORMAT(hora,'%H:%i') FROM citas WHERE id=:id"),{'id':own}).scalar_one()=='09:00'
