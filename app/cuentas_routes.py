from flask import Blueprint,g,request
from flask_jwt_extended import get_jwt
from sqlalchemy import text
from werkzeug.security import generate_password_hash,check_password_hash
from .api_common import ApiError,body,endpoint,engine,integer,page,query,response
from .usuarios_service import validar_registro
from .permisos import requiere_roles

cuentas=Blueprint('cuentas',__name__,url_prefix='/api/v1')


def revocar_usuario(c,id):
    c.execute(text('INSERT INTO sesiones_usuario(usuario_id,version) VALUES(:id,1) ON DUPLICATE KEY UPDATE version=version+1'),{'id':id})


@cuentas.post('/auth/logout')
@requiere_roles('administrador','personal','cliente')
@endpoint
def logout():
    claims=get_jwt()
    with engine().begin() as c:
        c.execute(text('INSERT IGNORE INTO tokens_revocados(jti,expira) VALUES(:jti,:exp)'),{'jti':claims['jti'],'exp':claims['exp']})
    return response(message='Sesión cerrada')


@cuentas.patch('/auth/password')
@requiere_roles('administrador','personal','cliente')
@endpoint
def password():
    d=body({'actual','nueva'},{'actual','nueva'})
    if not isinstance(d['actual'],str) or not isinstance(d['nueva'],str) or not 8<=len(d['nueva'])<=128 or not d['nueva'].strip():raise ApiError('Contraseñas inválidas. La nueva requiere de 8 a 128 caracteres.')
    with engine().begin() as c:
        row=c.execute(text('SELECT password_hash,activo FROM usuarios WHERE id=:id FOR UPDATE'),{'id':g.usuario_actual['id']}).mappings().one()
        if not row['activo'] or not check_password_hash(row['password_hash'],d['actual']):raise ApiError('La contraseña actual no es correcta.',401)
        c.execute(text('UPDATE usuarios SET password_hash=:hash WHERE id=:id'),{'hash':generate_password_hash(d['nueva'],method='scrypt'),'id':g.usuario_actual['id']})
        revocar_usuario(c,g.usuario_actual['id'])
    return response(message='Contraseña actualizada. Inicia sesión nuevamente.')


def editar_cuenta(id,admin=False):
    d=body({'nombre','email','telefono'})
    if not d:raise ApiError('Envía al menos un campo para modificar.')
    with engine().begin() as c:
        users={}
        for uid in sorted({id,g.usuario_actual['id']}):
            users[uid]=c.execute(text('SELECT * FROM usuarios WHERE id=:id FOR UPDATE'),{'id':uid}).mappings().first()
        current=users[g.usuario_actual['id']]
        if not current or not current['activo'] or (admin and current['rol']!='administrador'):raise ApiError('Cuenta no autorizada.',401)
        old=users[id]
        if not old:raise ApiError('Usuario no encontrado.',404)
        fields={k:d.get(k,old[k]) for k in ('nombre','email','telefono')}
        valid=validar_registro({**fields,'password':'VALIDACION_INTERNA_NO_SE_GUARDA'})
        c.execute(text('UPDATE usuarios SET nombre=:nombre,email=:email,telefono=:telefono WHERE id=:id'),{**valid,'id':id})
    return response({'id':id,**{k:valid[k] for k in fields}})


@cuentas.patch('/auth/perfil')
@requiere_roles('administrador','personal','cliente')
@endpoint
def editar_mi_perfil():return editar_cuenta(g.usuario_actual['id'])


@cuentas.patch('/admin/usuarios/<int:usuario_id>')
@requiere_roles('administrador')
@endpoint
def editar_usuario(usuario_id):return editar_cuenta(usuario_id,True)


@cuentas.post('/admin/usuarios')
@requiere_roles('administrador')
@endpoint
def crear_usuario():
    d=body({'nombre','email','telefono','password','rol'},{'nombre','password','rol'})
    rol=d.pop('rol')
    if rol not in ('cliente','personal','administrador'):raise ApiError('Rol inválido.')
    valid=validar_registro(d)
    from .api_common import actor
    with engine().begin() as c:
        actor(c,{'administrador'})
        id=c.execute(text('INSERT INTO usuarios(nombre,email,telefono,password_hash,rol) VALUES(:nombre,:email,:telefono,:hash,:rol)'),{**valid,'hash':generate_password_hash(valid['password'],method='scrypt'),'rol':rol}).lastrowid
    valid.pop('password')
    return response({'id':id,**valid,'rol':rol,'activo':True},status=201)


@cuentas.patch('/admin/usuarios/<int:usuario_id>/rol')
@requiere_roles('administrador')
@endpoint
def cambiar_rol(usuario_id):
    d=body({'rol'},{'rol'})
    if d['rol'] not in ('cliente','personal','administrador'):raise ApiError('Rol inválido.')
    if usuario_id==g.usuario_actual['id']:raise ApiError('No puedes cambiar tu propio rol.',409)
    with engine().begin() as c:
        users={}
        for id in sorted({usuario_id,g.usuario_actual['id']}):
            users[id]=c.execute(text('SELECT * FROM usuarios WHERE id=:id FOR UPDATE'),{'id':id}).mappings().first()
        admin=users[g.usuario_actual['id']];u=users[usuario_id]
        if not admin or not admin['activo'] or admin['rol']!='administrador':raise ApiError('Cuenta no autorizada.',401)
        if not u:raise ApiError('Usuario no encontrado.',404)
        if u['rol']==d['rol']:return response({'id':usuario_id,'rol':d['rol']})
        # Conserva las relaciones semánticas de cuentas que ya operaron.
        dependencies=[('citas','cliente_id'),('citas','personal_id'),('disponibilidades','personal_id'),('pedidos','usuario_id'),('puntos_historial','usuario_id')]
        for table,col in dependencies:
            if c.execute(text(f'SELECT 1 FROM {table} WHERE {col}=:id LIMIT 1'),{'id':usuario_id}).first():
                raise ApiError('La cuenta tiene historial asociado a su rol. Conserva el rol y crea otra cuenta para la nueva función.',409)
        if u['puntos']:raise ApiError('La cuenta conserva puntos.',409)
        c.execute(text('UPDATE usuarios SET rol=:rol WHERE id=:id'),{'rol':d['rol'],'id':usuario_id})
        revocar_usuario(c,usuario_id)
    return response({'id':usuario_id,'rol':d['rol']})


@cuentas.get('/admin/clientes')
@requiere_roles('administrador')
@endpoint
def buscar_clientes():
    query(('q',));g.query_allowed=('q',)
    value=request.args.get('q','').strip()
    if len(value)>150:raise ApiError('Búsqueda demasiado larga.')
    # LOCATE busca texto literal; no interpreta porcentajes como comodines.
    with engine().connect() as c:return page(c,"SELECT id,nombre,email,telefono,activo,puntos FROM usuarios WHERE rol='cliente' AND (LOCATE(:q,nombre)>0 OR LOCATE(:q,COALESCE(email,''))>0 OR LOCATE(:q,COALESCE(telefono,''))>0) ORDER BY nombre,id",{'q':value})


@cuentas.get('/admin/clientes/<int:cliente_id>/citas')
@requiere_roles('administrador')
@endpoint
def historial_cliente(cliente_id):
    with engine().connect() as c:
        if not c.execute(text("SELECT id FROM usuarios WHERE id=:id AND rol='cliente'"),{'id':cliente_id}).first():raise ApiError('Cliente no encontrado.',404)
        return page(c,"SELECT c.id,c.servicio_id,s.nombre AS servicio,c.personal_id,c.fecha,TIME_FORMAT(c.hora,'%H:%i') AS hora,c.duracion_min,c.estado,c.notas FROM citas c JOIN servicios s ON s.id=c.servicio_id WHERE cliente_id=:id ORDER BY fecha DESC,hora DESC,c.id DESC",{'id':cliente_id})
