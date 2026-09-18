from datetime import datetime,timedelta
from flask import Blueprint,request
from sqlalchemy import text
from .api_common import ApiError,actor,body,boolean,endpoint,engine,response
from .personal_service import validar_horario
from .disponibilidad_service import ZONA_NEGOCIO,unir_fecha_hora
from .permisos import requiere_roles

horarios=Blueprint('horarios',__name__,url_prefix='/api/v1/admin')


@horarios.get('/personal/<int:personal_id>/disponibilidades')
@requiere_roles('administrador')
@endpoint
def horarios_admin(personal_id):
    with engine().connect() as c:
        rows=c.execute(text("SELECT id,personal_id,dia_semana,TIME_FORMAT(hora_inicio,'%H:%i') AS hora_inicio,TIME_FORMAT(hora_fin,'%H:%i') AS hora_fin,activo FROM disponibilidades WHERE personal_id=:id ORDER BY dia_semana,hora_inicio,id"),{'id':personal_id}).mappings().all()
    return response([dict(r) for r in rows])


def cambiar(id,estado=False):
    d=body({'activo'},{'activo'}) if estado else body({'dia_semana','hora_inicio','hora_fin'},{'dia_semana','hora_inicio','hora_fin'})
    if estado:boolean(d['activo'])
    else:d=validar_horario(d)
    with engine().connect() as c:
        ref=c.execute(text('SELECT personal_id FROM disponibilidades WHERE id=:id'),{'id':id}).mappings().first()
    if not ref:raise ApiError('Horario no encontrado.',404)
    with engine().begin() as c:
        from flask import g
        for uid in sorted({ref['personal_id'],g.usuario_actual['id']}):
            row=c.execute(text('SELECT rol,activo FROM usuarios WHERE id=:id FOR UPDATE'),{'id':uid}).mappings().first()
            if uid==g.usuario_actual['id'] and (not row or not row['activo'] or row['rol']!='administrador'):raise ApiError('Cuenta no autorizada.',401)
        rows=[dict(r) for r in c.execute(text("SELECT id,personal_id,dia_semana,TIME_FORMAT(hora_inicio,'%H:%i') AS hora_inicio,TIME_FORMAT(hora_fin,'%H:%i') AS hora_fin,activo FROM disponibilidades WHERE personal_id=:id ORDER BY id FOR UPDATE"),{'id':ref['personal_id']}).mappings()]
        original=next((r for r in rows if r['id']==id),None)
        if not original:raise ApiError('Horario no encontrado.',404)
        updated={**original,**d}
        proposed=[updated if r['id']==id else r for r in rows]
        active=[r for r in proposed if r['activo']]
        for i,a in enumerate(active):
            for b in active[i+1:]:
                if a['dia_semana']==b['dia_semana'] and a['hora_inicio']<b['hora_fin'] and a['hora_fin']>b['hora_inicio']:raise ApiError('El bloque se superpone con otro horario.',409)
        now=datetime.now(ZONA_NEGOCIO)
        appointments=c.execute(text("SELECT fecha,TIME_FORMAT(hora,'%H:%i') AS hora,duracion_min FROM citas WHERE personal_id=:id AND fecha>=:today AND estado IN ('pendiente','confirmada') FOR UPDATE"),{'id':ref['personal_id'],'today':now.date()}).mappings()
        for cita in appointments:
            start=unir_fecha_hora(cita['fecha'],cita['hora']);end=start+timedelta(minutes=cita['duracion_min'])
            if end<=now:continue
            if not any(b['dia_semana']==cita['fecha'].isoweekday() and unir_fecha_hora(cita['fecha'],b['hora_inicio'])<=start and unir_fecha_hora(cita['fecha'],b['hora_fin'])>=end for b in active):
                raise ApiError('El cambio deja una cita vigente fuera del horario. Reprograma o cancela esa cita primero.',409)
        c.execute(text('UPDATE disponibilidades SET dia_semana=:dia_semana,hora_inicio=:hora_inicio,hora_fin=:hora_fin,activo=:activo WHERE id=:id'),updated)
    return response(updated)


@horarios.put('/disponibilidades/<int:horario_id>')
@requiere_roles('administrador')
@endpoint
def editar_horario(horario_id):return cambiar(horario_id)


@horarios.patch('/disponibilidades/<int:horario_id>/estado')
@requiere_roles('administrador')
@endpoint
def estado_horario(horario_id):return cambiar(horario_id,True)


@horarios.patch('/citas/<int:cita_id>/estado')
@requiere_roles('administrador')
@endpoint
def estado_cita_admin(cita_id):
    from flask import g
    d=body({'estado'},{'estado'})
    if d['estado'] not in ('confirmada','completada','cancelada'):raise ApiError('Estado inválido.')
    with engine().connect() as c:
        ref=c.execute(text('SELECT cliente_id,personal_id FROM citas WHERE id=:id'),{'id':cita_id}).mappings().first()
    if not ref:raise ApiError('Cita no encontrada.',404)
    with engine().begin() as c:
        for uid in sorted({id for id in (g.usuario_actual['id'],ref['cliente_id'],ref['personal_id']) if id is not None}):
            u=c.execute(text('SELECT rol,activo FROM usuarios WHERE id=:id FOR UPDATE'),{'id':uid}).mappings().first()
            if uid==g.usuario_actual['id'] and (not u or not u['activo'] or u['rol']!='administrador'):raise ApiError('Cuenta no autorizada.',401)
        cita=c.execute(text("SELECT estado,fecha,TIME_FORMAT(hora,'%H:%i') AS hora,duracion_min FROM citas WHERE id=:id FOR UPDATE"),{'id':cita_id}).mappings().first()
        if not cita:raise ApiError('Cita no encontrada.',404)
        if cita['estado']==d['estado']:return response({'id':cita_id,'estado':d['estado']})
        if cita['estado'] in ('completada','cancelada'):raise ApiError('Una cita finalizada no cambia de estado.',409)
        inicio=unir_fecha_hora(cita['fecha'],cita['hora']);fin=inicio+timedelta(minutes=cita['duracion_min']);now=datetime.now(ZONA_NEGOCIO)
        if d['estado']=='confirmada' and (cita['estado']!='pendiente' or inicio<=now):raise ApiError('Solo se confirman citas pendientes futuras.',409)
        if d['estado']=='completada' and (cita['estado']!='confirmada' or fin>now):raise ApiError('Solo se completan citas confirmadas después de su hora final.',409)
        c.execute(text('UPDATE citas SET estado=:estado WHERE id=:id'),{'estado':d['estado'],'id':cita_id})
    return response({'id':cita_id,'estado':d['estado']})
