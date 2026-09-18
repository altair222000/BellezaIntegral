from datetime import datetime
from flask import Blueprint,g
from sqlalchemy import text
from .api_common import ApiError,actor,body,boolean,date_value,endpoint,engine,integer,key,page,response,string
from .disponibilidad_service import ZONA_NEGOCIO
from .permisos import requiere_roles
from .db_context import cambio_puntos_controlado

fidelizacion=Blueprint('fidelizacion',__name__,url_prefix='/api/v1')
FIELDS={'titulo','descripcion','descuento_porcentaje','fecha_inicio','fecha_fin','puntos_costo'}


def validar_promocion(d):
    d['titulo']=string(d.get('titulo'),'titulo',120)
    d['descripcion']=string(d.get('descripcion'),'descripcion',255,True)
    integer(d.get('descuento_porcentaje'),'descuento_porcentaje',0,100)
    d['fecha_inicio']=date_value(d.get('fecha_inicio'));d['fecha_fin']=date_value(d.get('fecha_fin'))
    if d['fecha_fin']<d['fecha_inicio']:raise ApiError('fecha_fin debe ser igual o posterior a fecha_inicio.')
    d['puntos_costo']=integer(d.get('puntos_costo',0),'puntos_costo',0,1000000)
    if d['puntos_costo'] and not d['descripcion']:raise ApiError('Describe el beneficio y sus condiciones de canje.')
    return d


@fidelizacion.get('/promociones')
@endpoint
def promociones_vigentes():
    with engine().connect() as c:return page(c,'SELECT * FROM vw_promociones_vigentes ORDER BY id DESC')


@fidelizacion.get('/admin/promociones')
@requiere_roles('administrador')
@endpoint
def promociones_admin():
    with engine().connect() as c:return page(c,'SELECT * FROM promociones ORDER BY id DESC')


@fidelizacion.post('/admin/promociones')
@requiere_roles('administrador')
@endpoint
def crear_promocion():
    d=validar_promocion(body(FIELDS,{'titulo','descuento_porcentaje','fecha_inicio','fecha_fin'}))
    with engine().begin() as c:
        actor(c,{'administrador'})
        id=c.execute(text('INSERT INTO promociones(titulo,descripcion,descuento_porcentaje,fecha_inicio,fecha_fin,puntos_costo) VALUES(:titulo,:descripcion,:descuento_porcentaje,:fecha_inicio,:fecha_fin,:puntos_costo)'),d).lastrowid
    return response({'id':id,**d,'activa':True},status=201)


@fidelizacion.put('/admin/promociones/<int:promocion_id>')
@requiere_roles('administrador')
@endpoint
def modificar_promocion(promocion_id):
    d=validar_promocion(body(FIELDS,{'titulo','descuento_porcentaje','fecha_inicio','fecha_fin'}))
    with engine().begin() as c:
        actor(c,{'administrador'})
        if not c.execute(text('SELECT id FROM promociones WHERE id=:id FOR UPDATE'),{'id':promocion_id}).first():raise ApiError('Promoción no encontrada.',404)
        c.execute(text('UPDATE promociones SET titulo=:titulo,descripcion=:descripcion,descuento_porcentaje=:descuento_porcentaje,fecha_inicio=:fecha_inicio,fecha_fin=:fecha_fin,puntos_costo=:puntos_costo WHERE id=:id'),{**d,'id':promocion_id})
    return response({'id':promocion_id,**d})


@fidelizacion.patch('/admin/promociones/<int:promocion_id>/estado')
@requiere_roles('administrador')
@endpoint
def estado_promocion(promocion_id):
    active=boolean(body({'activa'},{'activa'})['activa'],'activa')
    with engine().begin() as c:
        actor(c,{'administrador'})
        if not c.execute(text('SELECT id FROM promociones WHERE id=:id FOR UPDATE'),{'id':promocion_id}).first():raise ApiError('Promoción no encontrada.',404)
        c.execute(text('UPDATE promociones SET activa=:active WHERE id=:id'),{'active':active,'id':promocion_id})
    return response({'id':promocion_id,'activa':active})


@fidelizacion.get('/puntos')
@requiere_roles('cliente')
@endpoint
def saldo_puntos():
    with engine().connect() as c:
        saldo=c.execute(text('SELECT puntos FROM usuarios WHERE id=:id'),{'id':g.usuario_actual['id']}).scalar_one()
    return response({'puntos':saldo})


@fidelizacion.get('/puntos/historial')
@requiere_roles('cliente')
@endpoint
def historial_puntos():
    with engine().connect() as c:return page(c,'SELECT * FROM puntos_historial WHERE usuario_id=:id ORDER BY id DESC',{'id':g.usuario_actual['id']})


@fidelizacion.post('/admin/puntos/asignar')
@requiere_roles('administrador')
@endpoint
def asignar_puntos():
    d=body({'cita_id','puntos','motivo'},{'cita_id','puntos','motivo'})
    integer(d['cita_id'],'cita_id');integer(d['puntos'],'puntos',1,1000000);d['motivo']=string(d['motivo'],'motivo',150)
    with engine().connect() as c:
        ref=c.execute(text('SELECT cliente_id FROM citas WHERE id=:id'),{'id':d['cita_id']}).mappings().first()
    if not ref:raise ApiError('Cita no encontrada.',404)
    with engine().begin() as c:
        # Orden compartido con reservas y cambios de cuenta.
        users={}
        for id in sorted({ref['cliente_id'],g.usuario_actual['id']}):
            users[id]=c.execute(text('SELECT id,rol,activo,puntos FROM usuarios WHERE id=:id FOR UPDATE'),{'id':id}).mappings().one()
        u=users[g.usuario_actual['id']];client=users[ref['cliente_id']]
        if not u['activo'] or u['rol']!='administrador':raise ApiError('Cuenta no autorizada.',401)
        if client['rol']!='cliente':raise ApiError('La cuenta no tiene rol cliente.',409)
        cita=c.execute(text('SELECT estado,cliente_id FROM citas WHERE id=:id FOR UPDATE'),{'id':d['cita_id']}).mappings().first()
        if not cita or cita['cliente_id']!=client['id'] or cita['estado']!='completada':raise ApiError('Solo se asignan puntos por una cita completada.',409)
        old=c.execute(text('SELECT id,puntos,motivo FROM puntos_historial WHERE cita_id=:id'),{'id':d['cita_id']}).mappings().first()
        if old:
            if old['puntos']!=d['puntos'] or old['motivo']!=d['motivo']:raise ApiError('Esta cita ya tiene una asignación diferente.',409)
            return response({'id':old['id'],'cambio_realizado':False})
        if client['puntos']+d['puntos']>4294967295:raise ApiError('Saldo fuera de rango.',409)
        with cambio_puntos_controlado(c):
            id=c.execute(text('INSERT INTO puntos_historial(usuario_id,puntos,motivo,cita_id) VALUES(:usuario,:puntos,:motivo,:cita_id)'),{**d,'usuario':client['id']}).lastrowid
            c.execute(text('UPDATE usuarios SET puntos=puntos+:p WHERE id=:id'),{'p':d['puntos'],'id':client['id']})
    return response({'id':id,'puntos':d['puntos'],'cambio_realizado':True},status=201)


@fidelizacion.post('/puntos/canjear')
@requiere_roles('cliente')
@endpoint
def canjear_puntos():
    d=body({'promocion_id','clave_operacion'},{'promocion_id','clave_operacion'})
    integer(d['promocion_id'],'promocion_id');key(d['clave_operacion'])
    with engine().begin() as c:
        u=actor(c,{'cliente'})
        old=c.execute(text('SELECT id,promocion_id,puntos,motivo FROM puntos_historial WHERE usuario_id=:u AND clave_operacion=:clave'),{'u':u['id'],'clave':d['clave_operacion']}).mappings().first()
        if old:
            if old['promocion_id']!=d['promocion_id']:raise ApiError('Clave usada para otra promoción.',409)
            return response(dict(old),message='Canje ya registrado')
        promo=c.execute(text('SELECT * FROM promociones WHERE id=:id FOR SHARE'),{'id':d['promocion_id']}).mappings().first()
        today=datetime.now(ZONA_NEGOCIO).date()
        if not promo or not promo['activa'] or not promo['fecha_inicio']<=today<=promo['fecha_fin'] or promo['puntos_costo']==0:
            raise ApiError('No es un beneficio canjeable vigente.',409)
        saldo=c.execute(text('SELECT puntos FROM usuarios WHERE id=:id'),{'id':u['id']}).scalar_one()
        if saldo<promo['puntos_costo']:raise ApiError('Puntos insuficientes.',409)
        motivo=('Canje: '+promo['titulo'])[:150]
        with cambio_puntos_controlado(c):
            id=c.execute(text('INSERT INTO puntos_historial(usuario_id,puntos,motivo,promocion_id,clave_operacion) VALUES(:u,:p,:motivo,:promo,:clave)'),{'u':u['id'],'p':-promo['puntos_costo'],'motivo':motivo,'promo':promo['id'],'clave':d['clave_operacion']}).lastrowid
            c.execute(text('UPDATE usuarios SET puntos=puntos-:p WHERE id=:id'),{'p':promo['puntos_costo'],'id':u['id']})
    return response({'id':id,'puntos_canjeados':promo['puntos_costo'],'saldo':saldo-promo['puntos_costo'],'beneficio':promo['titulo']},message='Canje registrado para entrega del beneficio en el salón',status=201)


@fidelizacion.get('/admin/puntos/historial')
@requiere_roles('administrador')
@endpoint
def historial_puntos_admin():
    with engine().connect() as c:return page(c,'SELECT h.*,u.nombre AS cliente FROM puntos_historial h JOIN usuarios u ON u.id=h.usuario_id ORDER BY h.id DESC')
