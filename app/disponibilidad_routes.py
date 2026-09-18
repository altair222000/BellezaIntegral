from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from .disponibilidad_service import (
    RecursoNoDisponible,
    calcular_disponibilidad,
)


disponibilidad = Blueprint(
    "disponibilidad",
    __name__,
    url_prefix="/api/v1/disponibilidad",
)


def error(mensaje, codigo):
    return jsonify({
        "success": False,
        "message": mensaje,
        "data": None,
    }), codigo


@disponibilidad.get("")
def consultar_disponibilidad():
    try:
        personal_id = int(request.args.get("personal_id", ""))
        servicio_id = int(request.args.get("servicio_id", ""))

        if not (
            1 <= personal_id <= 4294967295
            and 1 <= servicio_id <= 4294967295
        ):
            raise ValueError()

    except ValueError:
        return error(
            "personal_id y servicio_id deben ser identificadores válidos.",
            400,
        )

    try:
        motor = current_app.extensions["db_engine"]

        resultado = calcular_disponibilidad(
            motor,
            personal_id,
            servicio_id,
            request.args.get("fecha"),
        )

    except ValueError as exc:
        return error(str(exc), 400)

    except RecursoNoDisponible as exc:
        return error(str(exc), 404)

    except SQLAlchemyError:
        current_app.logger.error(
            "Error al consultar disponibilidad."
        )
        return error(
            "No fue posible consultar la disponibilidad.",
            500,
        )

    respuesta = jsonify({
        "success": True,
        "message": "Disponibilidad consultada correctamente",
        "data": resultado,
    })

    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta, 200