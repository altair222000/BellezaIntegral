from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from .permisos import requiere_roles
from .personal_service import (
    HorarioEnConflicto,
    listar_personal,
    consultar_horarios,
    registrar_horario,
)


personal = Blueprint(
    "personal",
    __name__,
    url_prefix="/api/v1/personal",
)


def error(mensaje, codigo):
    return jsonify({
        "success": False,
        "message": mensaje,
        "data": None,
    }), codigo


@personal.get("")
def consultar_personal():
    try:
        motor = current_app.extensions["db_engine"]
        registros = listar_personal(motor)

    except SQLAlchemyError:
        current_app.logger.error("Error al consultar personal.")
        return error("No fue posible consultar el personal.", 500)

    return jsonify({
        "success": True,
        "message": "Personal consultado correctamente",
        "data": registros,
    }), 200


@personal.get("/<int:personal_id>/disponibilidades")
def obtener_disponibilidades(personal_id):
    try:
        motor = current_app.extensions["db_engine"]
        horarios = consultar_horarios(motor, personal_id)

    except SQLAlchemyError:
        current_app.logger.error("Error al consultar horarios.")
        return error("No fue posible consultar los horarios.", 500)

    if horarios is None:
        return error("El profesional no está disponible.", 404)

    return jsonify({
        "success": True,
        "message": "Horario semanal consultado correctamente",
        "data": horarios,
    }), 200


@personal.post("/<int:personal_id>/disponibilidades")
@requiere_roles("administrador")
def crear_disponibilidad(personal_id):
    if not request.is_json:
        return error("Debes enviar application/json.", 415)

    try:
        motor = current_app.extensions["db_engine"]

        horario = registrar_horario(
            motor,
            personal_id,
            request.get_json(silent=True),
        )

    except ValueError as exc:
        return error(str(exc), 400)

    except HorarioEnConflicto as exc:
        return error(str(exc), 409)

    except SQLAlchemyError:
        current_app.logger.error("Error al registrar horario.")
        return error("No fue posible registrar el horario.", 500)

    if horario is None:
        return error("El profesional no está disponible.", 404)

    return jsonify({
        "success": True,
        "message": "Horario registrado correctamente",
        "data": horario,
    }), 201