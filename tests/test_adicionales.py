import time
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import text
from test_flujos import call,catalog,product,pedido


def test_reprogramacion_conflicto_conserva_original(client,headers,motor):
    s,date,_=catalog(client,headers)
    def book(hour,id):return call(client,headers,'/citas','POST',{'personal_id':3,'servicio_id':s,'fecha':date,'hora':hour},id=id,expected=201)['data']['id']
    cita=book('09:00',2);book('11:00',4)
    call(client,headers,f'/citas/{cita}/reprogramar','PATCH',{'fecha':date,'hora':'11:00'},id=2,expected=409)
    with motor.connect() as c:assert c.execute(text("SELECT TIME_FORMAT(hora,'%H:%i') FROM citas WHERE id=:id"),{'id':cita}).scalar_one()=='09:00'


def test_estado_administrativo(client,headers):
    s,date,block=catalog(client,headers)
    cita=call(client,headers,'/citas','POST',{'personal_id':3,'servicio_id':s,'fecha':date,'hora':'09:00'},id=2,expected=201)['data']['id']
    call(client,headers,f'/admin/citas/{cita}/estado','PATCH',{'estado':'confirmada'},id=2,expected=403)
    call(client,headers,f'/admin/citas/{cita}/estado','PATCH',{'estado':'confirmada'})
    call(client,headers,f'/admin/citas/{cita}/estado','PATCH',{'estado':'completada'},expected=409)
    call(client,headers,'/admin/usuarios/3/estado','PATCH',{'activo':False})
    call(client,headers,f'/admin/citas/{cita}/estado','PATCH',{'estado':'cancelada'})
    call(client,headers,f'/admin/disponibilidades/{block}/estado','PATCH',{'activo':False})


def test_compra_fallida_sin_movimientos_parciales(client,headers,motor):
    p=product(client,headers,2);q=product(client,headers,1)
    d=pedido(p);d['items'].append({'producto_id':q,'cantidad':2})
    call(client,headers,'/pedidos','POST',d,id=2,expected=409)
    with motor.connect() as c:
        assert c.execute(text('SELECT stock FROM productos WHERE id=:id'),{'id':p}).scalar_one()==2
        assert c.execute(text('SELECT COUNT(*) FROM pedidos')).scalar_one()==0


def test_20_consultas_simultaneas(app,client,headers):
    s,date,_=catalog(client,headers)
    def read(i):
        with app.test_client() as c:
            start=time.perf_counter();r=c.get(f'/api/v1/disponibilidad?personal_id=3&servicio_id={s}&fecha={date}')
            return r.status_code,time.perf_counter()-start
    with ThreadPoolExecutor(max_workers=20) as e:results=list(e.map(read,range(20)))
    assert all(code==200 for code,_ in results)
    # Medición informativa local; no convierte la prueba en SLA del despliegue.
    print('20 consultas, máximo segundos:',max(duration for _,duration in results))
