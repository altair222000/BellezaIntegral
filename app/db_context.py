"""Contexto de auditoría y banderas controladas para MySQL.

La capa SQL de integridad usa variables de sesión (@app_*, @permitir_*).
Estas funciones centralizan su uso para evitar escrituras que rompan los
triggers de stock/puntos y para que la auditoría conserve el actor/IP.
"""
from flask import g, has_request_context, request
from sqlalchemy import text


def actor_id_actual():
    if not has_request_context():
        return None
    usuario = getattr(g, "usuario_actual", None)
    if not isinstance(usuario, dict):
        return None
    return usuario.get("id")


def ip_actual():
    if not has_request_context():
        return None
    return request.remote_addr


def establecer_contexto_auditoria(conexion, actor_id=None):
    """Establece contexto explícito para una transacción ya abierta."""
    if actor_id is None:
        actor_id = actor_id_actual()
    conexion.execute(
        text(
            "SET @app_usuario_id=:actor_id, "
            "@app_ip=:ip, @app_correlacion_id=UUID()"
        ),
        {"actor_id": actor_id, "ip": ip_actual()},
    )


def permitir_cambio_stock(conexion, permitir=True):
    conexion.execute(
        text("SET @permitir_cambio_stock = :valor"),
        {"valor": 1 if permitir else None},
    )


def permitir_cambio_puntos(conexion, permitir=True):
    conexion.execute(
        text("SET @permitir_cambio_puntos = :valor"),
        {"valor": 1 if permitir else None},
    )

from contextlib import contextmanager


@contextmanager
def cambio_stock_controlado(conexion):
    permitir_cambio_stock(conexion, True)
    try:
        yield
    finally:
        try:
            permitir_cambio_stock(conexion, False)
        except Exception:
            # El checkout del pool vuelve a limpiar la variable si la transacción
            # quedó inválida por un error de MySQL.
            pass


@contextmanager
def cambio_puntos_controlado(conexion):
    permitir_cambio_puntos(conexion, True)
    try:
        yield
    finally:
        try:
            permitir_cambio_puntos(conexion, False)
        except Exception:
            pass
