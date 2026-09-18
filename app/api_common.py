"""Validadores y serialización compartidos por las ampliaciones v1."""
import re
from datetime import date, datetime
from decimal import Decimal
from functools import wraps
from flask import current_app, jsonify, request, g
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def clean(value):
    if isinstance(value, Decimal): return format(value, '.2f')
    if isinstance(value, (date, datetime)): return value.isoformat()
    if isinstance(value, dict):
        return {k: bool(v) if k in ('activo','activa') else clean(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [clean(v) for v in value]
    return value


def response(data=None, message='Operación realizada correctamente', status=200, meta=None):
    body={'success':status<400,'message':message,'data':clean(data)}
    if meta is not None: body['meta']=meta
    r=jsonify(body); r.headers['Cache-Control']='no-store'
    return r,status


def endpoint(fn):
    @wraps(fn)
    def run(*args,**kwargs):
        try: return fn(*args,**kwargs)
        except ApiError as e: return response(message=str(e),status=e.status)
        except ValueError as e: return response(message=str(e),status=400)
        except IntegrityError:
            return response(message='Los datos duplican un registro o incumplen una relación.',status=409)
        except DBAPIError as e:
            # SIGNAL SQLSTATE '45000' de MySQL llega normalmente como error 1644.
            args = getattr(getattr(e, 'orig', None), 'args', ())
            if args and args[0] == 1644:
                mensaje = str(args[1]) if len(args) > 1 else 'La operación fue rechazada por una regla de integridad.'
                return response(message=mensaje,status=409)
            current_app.logger.error('Fallo DBAPI en %s',fn.__name__)
            return response(message='No fue posible confirmar la operación. Consulta el estado antes de reintentar.',status=503)
        except SQLAlchemyError:
            current_app.logger.error('Fallo de base de datos en %s',fn.__name__)
            return response(message='No fue posible confirmar la operación. Consulta el estado antes de reintentar.',status=503)
    return run


def body(allowed,required=()):
    if not request.is_json: raise ApiError('Envía application/json.',415)
    d=request.get_json(silent=True)
    if not isinstance(d,dict): raise ApiError('Envía un objeto JSON válido.')
    if set(d)-set(allowed) or set(required)-set(d): raise ApiError('Campos no permitidos o campos obligatorios ausentes.')
    return d


def string(value,name,maximum,optional=False):
    if optional and value is None:return None
    if not isinstance(value,str) or not value.strip() or len(value.strip())>maximum:
        raise ApiError(f'{name} debe ser texto de 1 a {maximum} caracteres.')
    return value.strip()


def integer(value,name,minimum=1,maximum=4294967295):
    if type(value) is not int or not minimum<=value<=maximum: raise ApiError(f'{name} debe ser entero entre {minimum} y {maximum}.')
    return value


def boolean(value,name='activo'):
    if type(value) is not bool:raise ApiError(f'{name} debe ser true o false.')
    return value


def money(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{1,8}(\.\d{1,2})?',value):
        raise ApiError('precio debe ser texto decimal no negativo, por ejemplo 135.00.')
    return Decimal(value).quantize(Decimal('.01'))


def date_value(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value): raise ApiError('Fecha inválida: usa YYYY-MM-DD.')
    try:return date.fromisoformat(value)
    except ValueError:raise ApiError('La fecha no existe.') from None


def query(allowed=()):
    if set(request.args)-set(allowed)-{'pagina','limite'}:raise ApiError('Filtro no permitido.')
    if any(len(request.args.getlist(k))!=1 for k in request.args):raise ApiError('No repitas filtros.')
    try:p=int(request.args.get('pagina',1));l=int(request.args.get('limite',20))
    except ValueError:raise ApiError('pagina y limite deben ser enteros.') from None
    integer(p,'pagina',1,1000000);integer(l,'limite',1,100)
    return p,l


def page(conn,sql,params=None):
    p,l=query(getattr(g,'query_allowed',()))
    params={**(params or {}),'limite':l,'offset':(p-1)*l}
    total=conn.execute(text('SELECT COUNT(*) FROM ('+sql+') AS registros'),params).scalar_one()
    rows=conn.execute(text(sql+' LIMIT :limite OFFSET :offset'),params).mappings().all()
    return response([dict(r) for r in rows],meta={'pagina':p,'limite':l,'total':total,'cantidad':len(rows),'paginas':(total+l-1)//l})


def engine():return current_app.extensions['db_engine']


def actor(conn, roles=None):
    row=conn.execute(text('SELECT id,rol,activo FROM usuarios WHERE id=:id FOR UPDATE'),{'id':g.usuario_actual['id']}).mappings().first()
    if not row or not row['activo'] or (roles and row['rol'] not in roles):raise ApiError('La cuenta ya no está autorizada.',401)
    return row


def key(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,64}',value):raise ApiError('clave_operacion debe tener de 8 a 64 letras, números, guiones o guiones bajos.')
    return value
