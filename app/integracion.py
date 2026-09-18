"""Configuración compartida de API y clientes web/móvil."""
import os
import time
from threading import Lock
from collections import OrderedDict
from urllib.parse import urlsplit
from flask import jsonify,request,current_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException


def configurar_integracion(app):
    app.config['MAX_CONTENT_LENGTH']=1024*1024
    origins=set(filter(None,(s.strip() for s in os.getenv('CORS_ORIGINS','').split(','))))
    for origin in origins:
        parsed=urlsplit(origin)
        if origin=='*' or parsed.scheme not in ('http','https') or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
            raise RuntimeError('CORS_ORIGINS requiere orígenes exactos separados por coma, sin rutas ni comodín.')
    attempts=OrderedDict();lock=Lock()
    @app.before_request
    def limiter():
        if request.path=='/api/v1/auth/login' and request.method=='POST':
            now=time.monotonic();ip=request.remote_addr or 'unknown'
            with lock:
                # Protección local acotada. Para varios workers usar limitador compartido en proxy.
                old=attempts.pop(ip,[]);old=[t for t in old if now-t<60]
                if len(old)>=20:
                    attempts[ip]=old
                    r=jsonify(success=False,message='Demasiados intentos. Espera un minuto.',data=None);r.headers['Retry-After']='60'
                    return r,429
                old.append(now);attempts[ip]=old
                while len(attempts)>10000:attempts.popitem(last=False)
    @app.after_request
    def headers(r):
        r.headers['X-Content-Type-Options']='nosniff'
        r.headers['Referrer-Policy']='same-origin'
        if request.path.startswith('/api/'):
            r.headers['Cache-Control']='no-store'
            origin=request.headers.get('Origin')
            if origin in origins:
                r.headers['Access-Control-Allow-Origin']=origin
                r.vary.add('Origin')
                r.headers['Access-Control-Allow-Headers']='Authorization, Content-Type'
                r.headers['Access-Control-Allow-Methods']='GET, POST, PUT, PATCH, OPTIONS'
            if r.mimetype=='application/json':r.headers['Content-Type']='application/json; charset=utf-8'
        return r
    @app.errorhandler(HTTPException)
    def http_error(e):
        messages={400:'Solicitud inválida.',404:'Ruta no encontrada.',405:'Método no permitido.',413:'La solicitud excede 1 MiB.',415:'Envía application/json.'}
        # Conservar Allow y demás cabeceras HTTP generadas por Werkzeug.
        r=e.get_response();r.data=app.json.dumps({'success':False,'message':messages.get(e.code,'Solicitud rechazada.'),'data':None});r.content_type='application/json'
        return r
    @app.errorhandler(SQLAlchemyError)
    def db_error(e):
        app.logger.error('La operación no pudo comunicarse con la base de datos.')
        return jsonify(success=False,message='Base de datos no disponible o actualización pendiente.',data=None),503
    @app.errorhandler(500)
    def unexpected(e):
        return jsonify(success=False,message='No fue posible completar la operación.',data=None),500
