"""Consulta de auditoría. Las tablas son inmutables por diseño de la BD."""
from flask import Blueprint, g, request
from sqlalchemy import text

from .api_common import ApiError, endpoint, engine, page, query
from .permisos import requiere_roles


auditoria = Blueprint("auditoria", __name__, url_prefix="/api/v1/admin/auditoria")


@auditoria.get("/cambios")
@requiere_roles("administrador")
@endpoint
def cambios():
    query(("tabla", "operacion"))
    g.query_allowed = ("tabla", "operacion")
    filtros = []
    params = {}

    tabla = request.args.get("tabla")
    if tabla is not None:
        tabla = tabla.strip()
        if not tabla or len(tabla) > 64:
            raise ApiError("tabla no es válida.")
        filtros.append("tabla=:tabla")
        params["tabla"] = tabla

    operacion = request.args.get("operacion")
    if operacion is not None:
        operacion = operacion.upper()
        if operacion not in {"INSERT", "UPDATE", "DELETE"}:
            raise ApiError("operacion debe ser INSERT, UPDATE o DELETE.")
        filtros.append("operacion=:operacion")
        params["operacion"] = operacion

    where = " AND ".join(filtros) or "1=1"
    with engine().connect() as c:
        return page(
            c,
            "SELECT id,fecha_evento,usuario_app_id,ip_app,correlacion_id,"
            "tabla,registro_id,operacion,datos_anteriores,datos_nuevos "
            "FROM auditoria_cambios WHERE " + where + " ORDER BY id DESC",
            params,
        )


@auditoria.get("/eventos")
@requiere_roles("administrador")
@endpoint
def eventos():
    query(("tipo_evento", "entidad"))
    g.query_allowed = ("tipo_evento", "entidad")
    filtros = []
    params = {}

    for campo, limite in (("tipo_evento", 80), ("entidad", 64)):
        valor = request.args.get(campo)
        if valor is not None:
            valor = valor.strip()
            if not valor or len(valor) > limite:
                raise ApiError(f"{campo} no es válido.")
            filtros.append(f"{campo}=:{campo}")
            params[campo] = valor

    where = " AND ".join(filtros) or "1=1"
    with engine().connect() as c:
        return page(
            c,
            "SELECT id,fecha_evento,usuario_app_id,ip_app,correlacion_id,"
            "tipo_evento,entidad,entidad_id,detalle "
            "FROM auditoria_eventos WHERE " + where + " ORDER BY id DESC",
            params,
        )
