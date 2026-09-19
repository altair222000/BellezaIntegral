"""Catálogo, inventario y checkout demostrativo transaccional."""
import hashlib
import json
import re
from flask import Blueprint, g, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from sqlalchemy import text
from .permisos import requiere_roles
from .auth_service import consultar_perfil
from .suscripciones_service import descuento_productos_activo, precio_con_descuento
from .db_context import cambio_stock_controlado
from .api_common import (ApiError, actor, body, boolean, clean, endpoint, engine,
                         integer, key, money, page, query, response, string)

tienda=Blueprint('tienda',__name__,url_prefix='/api/v1')
PRODUCT_FIELDS={'nombre','descripcion','categoria','tipo','precio','imagen'}


def cliente_id_opcional():
    """Identifica un cliente si la solicitud incluye JWT; el catálogo sigue público."""
    verify_jwt_in_request(optional=True)
    identidad = get_jwt_identity()
    if not identidad:
        return None
    perfil = consultar_perfil(engine(), identidad)
    if not perfil or perfil["rol"] != "cliente":
        return None
    return perfil["id"]


def validar_producto(d):
    result={k:string(d.get(k),k,n,k in {'descripcion','imagen'}) for k,n in [('nombre',100),('descripcion',16000),('categoria',50),('imagen',255)]}
    if d.get('tipo') not in ('venta','insumo'):raise ApiError('tipo debe ser venta o insumo.')
    result['tipo']=d['tipo'];result['precio']=money(d.get('precio'))
    if d['tipo']=='insumo' and result['precio']!=0:raise ApiError('Los insumos tienen precio 0.00.')
    return result


@tienda.get('/productos')
@endpoint
def catalogo_productos():
    query()
    usuario_id = cliente_id_opcional()
    with engine().connect() as c:
        descuento = (
            descuento_productos_activo(c, usuario_id)
            if usuario_id
            else 0
        )
        return page(
            c,
            """
            SELECT
                id,
                nombre,
                descripcion,
                categoria,
                precio AS precio_original,
                ROUND(
                    precio * (100 - :descuento) / 100,
                    2
                ) AS precio,
                :descuento AS descuento_suscripcion,
                stock,
                imagen
            FROM productos
            WHERE activo=1
              AND tipo='venta'
            ORDER BY nombre,id
            """,
            {"descuento": descuento},
        )


@tienda.get('/admin/productos')
@requiere_roles('administrador')
@endpoint
def inventario():
    query(('tipo','activo'));g.query_allowed=('tipo','activo')
    filters=[];params={}
    if 'tipo' in request.args:
        if request.args['tipo'] not in ('venta','insumo'):raise ApiError('tipo inválido.')
        filters.append('tipo=:tipo');params['tipo']=request.args['tipo']
    if 'activo' in request.args:
        if request.args['activo'] not in ('true','false'):raise ApiError('activo inválido.')
        filters.append('activo=:activo');params['activo']=int(request.args['activo']=='true')
    with engine().connect() as c:return page(c,'SELECT * FROM productos WHERE '+(' AND '.join(filters) or '1=1')+' ORDER BY id',params)


@tienda.post('/admin/productos')
@requiere_roles('administrador')
@endpoint
def crear_producto():
    d=validar_producto(body(PRODUCT_FIELDS,{'nombre','categoria','tipo','precio'}))
    with engine().begin() as c:
        actor(c,{'administrador'})
        id=c.execute(text('INSERT INTO productos(nombre,descripcion,categoria,tipo,precio,imagen) VALUES(:nombre,:descripcion,:categoria,:tipo,:precio,:imagen)'),d).lastrowid
    return response({'id':id,**d,'activo':True,'stock':0},status=201)


@tienda.put('/admin/productos/<int:producto_id>')
@requiere_roles('administrador')
@endpoint
def modificar_producto(producto_id):
    d=validar_producto(body(PRODUCT_FIELDS,{'nombre','categoria','tipo','precio'}))
    with engine().begin() as c:
        actor(c,{'administrador'})
        old=c.execute(text('SELECT id,tipo FROM productos WHERE id=:id FOR UPDATE'),{'id':producto_id}).mappings().first()
        if not old:raise ApiError('Producto no encontrado.',404)
        if old['tipo']!=d['tipo']:raise ApiError('El tipo es permanente para conservar la clasificación del historial.',409)
        c.execute(text('UPDATE productos SET nombre=:nombre,descripcion=:descripcion,categoria=:categoria,precio=:precio,imagen=:imagen WHERE id=:id'),{**d,'id':producto_id})
    return response({'id':producto_id,**d})


@tienda.patch('/admin/productos/<int:producto_id>/estado')
@requiere_roles('administrador')
@endpoint
def estado_producto(producto_id):
    active=boolean(body({'activo'},{'activo'})['activo'])
    with engine().begin() as c:
        actor(c,{'administrador'})
        if not c.execute(text('SELECT id FROM productos WHERE id=:id FOR UPDATE'),{'id':producto_id}).first():raise ApiError('Producto no encontrado.',404)
        c.execute(text('UPDATE productos SET activo=:activo WHERE id=:id'),{'id':producto_id,'activo':active})
    return response({'id':producto_id,'activo':active})


@tienda.get('/admin/inventario/movimientos')
@requiere_roles('administrador')
@endpoint
def historial_inventario():
    query(('producto_id',));g.query_allowed=('producto_id',);params={};where='1=1'
    if 'producto_id' in request.args:
        params['id']=integer(int(request.args['producto_id']),'producto_id');where='m.producto_id=:id'
    with engine().connect() as c:return page(c,'SELECT m.*,p.nombre AS producto FROM movimientos_inventario m JOIN productos p ON p.id=m.producto_id WHERE '+where+' ORDER BY m.id DESC',params)


@tienda.post('/admin/inventario/movimientos')
@requiere_roles('administrador')
@endpoint
def movimiento_inventario():
    d=body({'producto_id','tipo','cantidad','motivo'},{'producto_id','tipo','cantidad','motivo'})
    integer(d['producto_id'],'producto_id');integer(d['cantidad'],'cantidad',1,1000000)
    d['motivo']=string(d['motivo'],'motivo',150)
    if d['tipo'] not in ('entrada','salida'):raise ApiError('tipo debe ser entrada o salida.')
    with engine().begin() as c:
        u=actor(c,{'administrador'})
        p=c.execute(text('SELECT stock FROM productos WHERE id=:id FOR UPDATE'),{'id':d['producto_id']}).mappings().first()
        if not p:raise ApiError('Producto no encontrado.',404)
        stock=p['stock']+(d['cantidad'] if d['tipo']=='entrada' else -d['cantidad'])
        if not 0<=stock<=4294967295:raise ApiError('El movimiento excede las existencias o el límite de stock.',409)
        with cambio_stock_controlado(c):
            c.execute(text('UPDATE productos SET stock=:stock WHERE id=:id'),{'stock':stock,'id':d['producto_id']})
            id=c.execute(text('INSERT INTO movimientos_inventario(producto_id,usuario_id,tipo,cantidad,motivo) VALUES(:producto_id,:usuario_id,:tipo,:cantidad,:motivo)'),{**d,'usuario_id':u['id']}).lastrowid
    return response({'id':id,'stock':stock,**d},status=201)


def pedido_json(c,id,owner=None):
    params={'id':id};sql='SELECT * FROM pedidos WHERE id=:id'
    if owner is not None:sql+=' AND usuario_id=:owner';params['owner']=owner
    row=c.execute(text(sql),params).mappings().first()
    if not row:raise ApiError('Pedido no encontrado.',404)
    result=dict(row);result.pop('solicitud_hash',None)
    result['detalle']=[dict(r) for r in c.execute(text('SELECT d.producto_id,p.nombre,d.cantidad,d.precio_unitario FROM pedido_detalle d JOIN productos p ON p.id=d.producto_id WHERE pedido_id=:id ORDER BY d.id'),{'id':id}).mappings()]
    result['pago_simulado']=True
    return result


@tienda.post('/pedidos')
@requiere_roles('cliente')
@endpoint
def crear_pedido():
    d=body({'items','nombre_entrega','telefono_entrega','direccion_entrega','metodo_pago','tarjeta_ultimos4','clave_operacion'}, {'items','nombre_entrega','telefono_entrega','direccion_entrega','metodo_pago','clave_operacion'})
    key(d['clave_operacion'])
    for field,n in [('nombre_entrega',100),('telefono_entrega',20),('direccion_entrega',255)]:d[field]=string(d[field],field,n)
    if not re.fullmatch(r'\+?[0-9]{8,15}',d['telefono_entrega']):raise ApiError('Teléfono inválido.')
    if d['metodo_pago'] not in ('efectivo','tarjeta_simulada'):raise ApiError('Método permitido: efectivo o tarjeta_simulada.')
    last=d.get('tarjeta_ultimos4')
    if d['metodo_pago']=='tarjeta_simulada':
        if not isinstance(last,str) or not re.fullmatch(r'[0-9]{4}',last):raise ApiError('Envía únicamente cuatro dígitos ficticios.')
    elif last is not None:raise ApiError('Efectivo no requiere datos de tarjeta.')
    d['tarjeta_ultimos4']=last
    if not isinstance(d['items'],list) or not 1<=len(d['items'])<=50:raise ApiError('Envía de 1 a 50 líneas.')
    quantities={}
    for item in d['items']:
        if not isinstance(item,dict) or set(item)!={'producto_id','cantidad'}:raise ApiError('Cada línea requiere producto_id y cantidad.')
        id=integer(item['producto_id'],'producto_id');q=integer(item['cantidad'],'cantidad',1,10000)
        if id in quantities:raise ApiError('No repitas productos.')
        quantities[id]=q
    fingerprint=hashlib.sha256(json.dumps(d,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    with engine().begin() as c:
        u=actor(c,{'cliente'})
        descuento_suscripcion=descuento_productos_activo(c,u['id'],bloquear=True)
        old=c.execute(text('SELECT id,solicitud_hash FROM pedidos WHERE usuario_id=:id AND clave_operacion=:clave'),{'id':u['id'],'clave':d['clave_operacion']}).mappings().first()
        if old:
            if old['solicitud_hash']!=fingerprint:raise ApiError('La clave_operacion ya se usó para otro contenido.',409)
            return response(pedido_json(c,old['id']),message='Pedido ya registrado')
        rows=[];total=0
        for id in sorted(quantities):
            p=c.execute(text('SELECT * FROM productos WHERE id=:id FOR UPDATE'),{'id':id}).mappings().first()
            if not p or not p['activo'] or p['tipo']!='venta':raise ApiError('Producto no disponible.',409)
            q=quantities[id]
            if p['stock']<q:raise ApiError('Existencias insuficientes para '+p['nombre'],409)
            precio_final=precio_con_descuento(p['precio'],descuento_suscripcion)
            total+=precio_final*q;rows.append((p,q,precio_final))
        if total>99999999.99:raise ApiError('El total excede el límite permitido.')
        id=c.execute(text('''INSERT INTO pedidos(usuario_id,total,nombre_entrega,telefono_entrega,direccion_entrega,metodo_pago,tarjeta_ultimos4,clave_operacion,solicitud_hash)
            VALUES(:usuario_id,:total,:nombre_entrega,:telefono_entrega,:direccion_entrega,:metodo_pago,:tarjeta_ultimos4,:clave_operacion,:solicitud_hash)'''),{**d,'usuario_id':u['id'],'total':total,'solicitud_hash':fingerprint}).lastrowid
        with cambio_stock_controlado(c):
            for p,q,precio_final in rows:
                c.execute(text('INSERT INTO pedido_detalle(pedido_id,producto_id,cantidad,precio_unitario) VALUES(:pedido,:producto,:q,:precio)'),{'pedido':id,'producto':p['id'],'q':q,'precio':precio_final})
                c.execute(text('UPDATE productos SET stock=stock-:q WHERE id=:id'),{'q':q,'id':p['id']})
                c.execute(text("INSERT INTO movimientos_inventario(producto_id,usuario_id,tipo,cantidad,motivo) VALUES(:p,:u,'salida',:q,:motivo)"),{'p':p['id'],'u':u['id'],'q':q,'motivo':f'Pedido {id} de demostración'})
        result=pedido_json(c,id)
        result['descuento_suscripcion']=descuento_suscripcion
    return response(result,status=201,message='Pedido de demostración registrado; no se realizó ningún cobro')


@tienda.get('/pedidos/mios')
@requiere_roles('cliente')
@endpoint
def mis_pedidos():
    with engine().connect() as c:return page(c,'SELECT id,fecha,total,estado,metodo_pago FROM pedidos WHERE usuario_id=:id ORDER BY id DESC',{'id':g.usuario_actual['id']})


@tienda.get('/pedidos/<int:pedido_id>')
@requiere_roles('cliente','administrador')
@endpoint
def detalle_pedido(pedido_id):
    with engine().connect() as c:return response(pedido_json(c,pedido_id,g.usuario_actual['id'] if g.usuario_actual['rol']=='cliente' else None))


@tienda.get('/admin/pedidos')
@requiere_roles('administrador')
@endpoint
def todos_pedidos():
    with engine().connect() as c:return page(c,'SELECT id,usuario_id,fecha,total,estado,metodo_pago FROM pedidos ORDER BY id DESC')


@tienda.patch('/admin/pedidos/<int:pedido_id>/cancelar')
@requiere_roles('administrador')
@endpoint
def cancelar_pedido(pedido_id):
    if request.get_data():raise ApiError('No envíes cuerpo para cancelar.')
    with engine().begin() as c:
        u=actor(c,{'administrador'})
        row=c.execute(text('SELECT * FROM pedidos WHERE id=:id FOR UPDATE'),{'id':pedido_id}).mappings().first()
        if not row:raise ApiError('Pedido no encontrado.',404)
        if row['estado']=='cancelado':return response({'id':pedido_id,'estado':'cancelado','cambio_realizado':False})
        details=c.execute(text('SELECT producto_id,cantidad FROM pedido_detalle WHERE pedido_id=:id ORDER BY producto_id'),{'id':pedido_id}).mappings().all()
        with cambio_stock_controlado(c):
            for d in details:
                p=c.execute(text('SELECT stock FROM productos WHERE id=:id FOR UPDATE'),{'id':d['producto_id']}).mappings().one()
                if p['stock']+d['cantidad']>4294967295:raise ApiError('El reintegro excede el límite de stock.',409)
                c.execute(text('UPDATE productos SET stock=stock+:q WHERE id=:id'),{'q':d['cantidad'],'id':d['producto_id']})
                c.execute(text("INSERT INTO movimientos_inventario(producto_id,usuario_id,tipo,cantidad,motivo) VALUES(:p,:u,'entrada',:q,:motivo)"),{'p':d['producto_id'],'u':u['id'],'q':d['cantidad'],'motivo':f'Cancelación pedido {pedido_id}'})
            c.execute(text("UPDATE pedidos SET estado='cancelado' WHERE id=:id"),{'id':pedido_id})
    return response({'id':pedido_id,'estado':'cancelado','cambio_realizado':True})
