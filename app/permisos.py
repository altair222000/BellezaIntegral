from functools import wraps

from flask import current_app, g, jsonify
from flask_jwt_extended import (
    get_jwt_identity,
    verify_jwt_in_request,
)
from sqlalchemy.exc import SQLAlchemyError

from .auth_service import consultar_perfil


def error_acceso(mensaje, codigo):
    return jsonify({
        "success": False,
        "message": mensaje,
        "data": None,
    }), codigo


def requiere_roles(*roles_permitidos):
    roles_validos = {"administrador", "personal", "cliente"}

    if (
        not roles_permitidos
        or not set(roles_permitidos).issubset(roles_validos)
    ):
        raise ValueError("La ruta debe declarar roles válidos.")

    def decorar(funcion):
        @wraps(funcion)
        def verificar(*args, **kwargs):
            # Comprueba firma, vigencia y presencia del token.
            verify_jwt_in_request()

            try:
                motor = current_app.extensions["db_engine"]

                usuario = consultar_perfil(
                    motor,
                    get_jwt_identity(),
                )

            except SQLAlchemyError:
                current_app.logger.error(
                    "No fue posible comprobar los permisos del usuario."
                )
                return error_acceso(
                    "No fue posible verificar el acceso.",
                    503,
                )

            # consultar_perfil solo devuelve cuentas activas.
            if usuario is None:
                return error_acceso(
                    "La cuenta no está disponible.",
                    401,
                )

            if usuario["rol"] not in roles_permitidos:
                return error_acceso(
                    "No tienes permisos para realizar esta operación.",
                    403,
                )

            # Disponible únicamente durante esta solicitud.
            g.usuario_actual = usuario

            return funcion(*args, **kwargs)

        return verificar

    return decorar