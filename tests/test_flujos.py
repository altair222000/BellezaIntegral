from datetime import datetime,timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from io import BytesIO
from sqlalchemy import text
from app.disponibilidad_service import ZONA_NEGOCIO


def call(client,headers,path,method='GET',data=None,id=1,expected=200):
    kwargs={'headers':headers(id)}
    if data is not None:kwargs['json']=data
    r=client.open('/api/v1'+path,method=method,**kwargs)
    assert r.status_code==expected,(path,r.status_code,r.get_data(as_text=True))
    return r.get_json()


def catalog(client,h):
    s=call(client,h,'/servicios','POST',{'nombre':'Manicura','categoria':'Uñas','duracion_min':60,'precio':'135.00'},expected=201)['data']['id']
    when=datetime.now(ZONA_NEGOCIO).date()+timedelta(days=7)
    block=call(client,h,'/personal/3/disponibilidades','POST',{'dia_semana':when.isoweekday(),'hora_inicio':'09:00','hora_fin':'17:00'},expected=201)['data']['id']
    return s,when.isoformat(),block


def product(client,h,stock=5):
    id=call(client,h,'/admin/productos','POST',{'nombre':'Esmalte','categoria':'Belleza','tipo':'venta','precio':'20.00'},expected=201)['data']['id']
    call(client,h,'/admin/inventario/movimientos','POST',{'producto_id':id,'tipo':'entrada','cantidad':stock,'motivo':'Prueba'},expected=201)
    return id


def pedido(p,key='pedido_prueba_1',cantidad=2):
    return {'items':[{'producto_id':p,'cantidad':cantidad}],'nombre_entrega':'Prueba','telefono_entrega':'55550101','direccion_entrega':'Dirección de prueba','metodo_pago':'efectivo','clave_operacion':key}


def test_auth_accounts(client,headers):
    r=call(client,headers,'/auth/login','POST',{'identificador':'cuenta2@example.com','password':'PasswordTest2026!'},id=2)
    token={'Authorization':'Bearer '+r['data']['access_token']}
    assert client.get('/api/v1/auth/perfil',headers=token).status_code==200
    assert client.post('/api/v1/auth/logout',headers=token).status_code==200
    assert client.get('/api/v1/auth/perfil',headers=token).status_code==401
    call(client,headers,'/auth/perfil','PATCH',{'nombre':'Nombre cambiado'},id=2)
    call(client,headers,'/auth/password','PATCH',{'actual':'PasswordTest2026!','nueva':'OtraPassword2026!'},id=2)
    call(client,headers,'/auth/perfil',id=2,expected=401)
    call(client,headers,'/auth/login','POST',{'identificador':'cuenta2@example.com','password':'OtraPassword2026!'},id=2)
    call(client,headers,'/admin/usuarios/1/estado','PATCH',{'activo':False},expected=409)
    call(client,headers,'/admin/usuarios/5/rol','PATCH',{'rol':'cliente'})
    call(client,headers,'/auth/perfil',id=5,expected=401)
    call(client,headers,'/admin/clientes?q=Cuenta')


def test_admin_access_and_input(client,headers):
    for path,method,data in [('/admin/productos','GET',None),('/admin/productos','POST',{}),('/admin/reportes/resumen','GET',None),('/admin/usuarios','POST',{}),('/admin/promociones','POST',{}),('/admin/inventario/movimientos','POST',{})]:
        call(client,headers,path,method,data,id=2,expected=403)
        assert client.open('/api/v1'+path,method=method,json=data).status_code==401
    call(client,headers,'/admin/productos','POST',{},expected=400)
    call(client,headers,'/admin/productos?pagina=0',expected=400)
    call(client,headers,'/admin/productos?tipo=x',expected=400)
    call(client,headers,'/admin/productos?pagina=1&pagina=2',expected=400)
    assert client.post('/api/v1/admin/productos',headers=headers(),data='text').status_code==415
    call(client,headers,'/admin/personal','POST',{'nombre':'Duplicado','email':'cuenta2@example.com','password':'PasswordTest2026!'},expected=409)
    r=client.get('/api/v1/productos',headers={'Origin':'http://localhost:5173'})
    assert r.headers['Access-Control-Allow-Origin']=='http://localhost:5173'
    assert 'Access-Control-Allow-Origin' not in client.get('/api/v1/productos',headers={'Origin':'https://other.invalid'}).headers
    assert client.put('/api/v1/productos').status_code==405
    assert client.post('/api/v1/auth/registro',data='x'*(1024*1024+1),content_type='application/json').status_code==413


def test_citas_horarios(client,headers,motor):
    s,date,block=catalog(client,headers)
    d={'personal_id':3,'servicio_id':s,'fecha':date,'hora':'09:00'}
    cita=call(client,headers,'/citas','POST',d,id=2,expected=201)['data']['id']
    call(client,headers,'/citas','POST',d,id=4,expected=409)
    call(client,headers,f'/citas/{cita}/reprogramar','PATCH',{'fecha':date,'hora':'11:00'},id=4,expected=404)
    call(client,headers,f'/admin/disponibilidades/{block}/estado','PATCH',{'activo':False},expected=409)
    call(client,headers,f'/citas/{cita}/reprogramar','PATCH',{'fecha':date,'hora':'11:00'},id=2)
    call(client,headers,f'/agenda/{cita}/estado','PATCH',{'estado':'confirmada'},id=3)
    call(client,headers,f'/agenda/{cita}/estado','PATCH',{'estado':'completada'},id=3,expected=409)
    call(client,headers,f'/agenda/{cita}/estado','PATCH',{'estado':'confirmada'},id=5,expected=404)
    call(client,headers,f'/citas/{cita}/cancelar','PATCH',id=2)
    call(client,headers,f'/admin/disponibilidades/{block}/estado','PATCH',{'activo':False})
    call(client,headers,'/admin/usuarios/3/rol','PATCH',{'rol':'cliente'},expected=409)
    assert call(client,headers,'/disponibilidad?personal_id=3&servicio_id='+str(s)+'&fecha='+date)['data']['horarios']==[]


def test_orders_inventory(client,headers,motor):
    p=product(client,headers)
    d=pedido(p);order=call(client,headers,'/pedidos','POST',d,id=2,expected=201)['data']
    assert order['total']=='40.00'
    same=call(client,headers,'/pedidos','POST',d,id=2)['data'];assert same['id']==order['id']
    call(client,headers,'/pedidos','POST',pedido(p,cantidad=1),id=2,expected=409)
    call(client,headers,'/pedidos/'+str(order['id']),id=4,expected=404)
    call(client,headers,'/pedidos','POST',pedido(p,'pedido_stock_2',4),id=4,expected=409)
    with motor.connect() as c:assert c.execute(text('SELECT stock FROM productos WHERE id=:id'),{'id':p}).scalar_one()==3
    call(client,headers,'/admin/pedidos/'+str(order['id'])+'/cancelar','PATCH')
    call(client,headers,'/admin/pedidos/'+str(order['id'])+'/cancelar','PATCH')
    with motor.connect() as c:assert c.execute(text('SELECT stock FROM productos WHERE id=:id'),{'id':p}).scalar_one()==5
    call(client,headers,'/admin/inventario/movimientos','POST',{'producto_id':p,'tipo':'salida','cantidad':6,'motivo':'Prueba'},expected=409)


def test_loyalty(client,headers,motor):
    s,date,block=catalog(client,headers)
    cita=call(client,headers,'/citas','POST',{'personal_id':3,'servicio_id':s,'fecha':date,'hora':'09:00'},id=2,expected=201)['data']['id']
    award={'cita_id':cita,'puntos':100,'motivo':'Atención completada de prueba'}
    call(client,headers,'/admin/puntos/asignar','POST',award,expected=409)
    # Fixture en BD aislada para cubrir el estado completada sin alterar reloj.
    with motor.begin() as c:
        ayer=datetime.now(ZONA_NEGOCIO).date()-timedelta(days=1)
        c.execute(text("UPDATE disponibilidades SET dia_semana=:dia WHERE id=:id"),{'dia':ayer.isoweekday(),'id':block})
        c.execute(text("UPDATE citas SET fecha=:ayer,estado='confirmada' WHERE id=:id"),{'ayer':ayer,'id':cita})
    call(client,headers,f'/agenda/{cita}/estado','PATCH',{'estado':'completada'},id=3)
    call(client,headers,'/admin/puntos/asignar','POST',award,expected=201)
    call(client,headers,'/admin/puntos/asignar','POST',award)
    today=datetime.now(ZONA_NEGOCIO).date().isoformat()
    promo=call(client,headers,'/admin/promociones','POST',{'titulo':'Beneficio','descripcion':'Entrega de beneficio en salón','descuento_porcentaje':0,'fecha_inicio':today,'fecha_fin':today,'puntos_costo':60},expected=201)['data']['id']
    d={'promocion_id':promo,'clave_operacion':'canje_prueba_1'}
    call(client,headers,'/puntos/canjear','POST',d,id=2,expected=201)
    call(client,headers,'/puntos/canjear','POST',d,id=2)
    assert call(client,headers,'/puntos',id=2)['data']['puntos']==40
    call(client,headers,'/puntos/canjear','POST',{**d,'clave_operacion':'canje_prueba_2'},id=2,expected=409)


def test_reports_export(client,headers):
    call(client,headers,'/admin/reportes/resumen')
    call(client,headers,'/admin/reportes/resumen?desde=2026-01-01&hasta=2028-01-01',expected=400)
    r=client.get('/api/v1/admin/reportes/citas.xlsx',headers=headers())
    assert r.status_code==200
    from openpyxl import load_workbook
    wb=load_workbook(BytesIO(r.data));assert wb.active['A1'].value=='id'
    assert client.get('/').status_code==200
    assert client.get('/visor/app.js').status_code==200


def test_concurrent_booking(app,client,headers):
    s,date,_=catalog(client,headers);barrier=Barrier(2)
    hs=[headers(2),headers(4)]
    def reserve(h):
        with app.test_client() as c:
            barrier.wait()
            return c.post('/api/v1/citas',json={'personal_id':3,'servicio_id':s,'fecha':date,'hora':'09:00'},headers=h).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:statuses=list(executor.map(reserve,hs))
    assert sorted(statuses)==[201,409],statuses


def test_concurrent_stock(app,client,headers,motor):
    p=product(client,headers,1);barrier=Barrier(2)
    hs=[headers(2),headers(4)]
    def purchase(h):
        with app.test_client() as c:
            barrier.wait()
            return c.post('/api/v1/pedidos',json=pedido(p,'stock_parallel_1',1),headers=h).status_code
    with ThreadPoolExecutor(max_workers=2) as ex:statuses=list(ex.map(purchase,hs))
    assert sorted(statuses)==[201,409],statuses
    with motor.connect() as c:assert c.execute(text('SELECT stock FROM productos WHERE id=:id'),{'id':p}).scalar_one()==0
