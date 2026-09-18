from datetime import datetime

from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from .disponibilidad_service import ZONA_NEGOCIO
from .permisos import requiere_roles
from .agenda_service import (
    EstadoAgendaInvalido,
    PersonalNoDisponible,
    consultar_agenda,
    cambiar_estado_agenda,
)


agenda = Blueprint(
    "agenda",
    __name__,
    url_prefix="/api/v1/agenda",
)


def error(mensaje, codigo):
    return jsonify({
        "success": False,
        "message": mensaje,
        "data": None,
    }), codigo


@agenda.get("")
@requiere_roles("personal")
def obtener_agenda():
    fecha = request.args.get(
        "fecha",
        datetime.now(ZONA_NEGOCIO).date().isoformat(),
    )

    try:
        motor = current_app.extensions["db_engine"]

        registros = consultar_agenda(
            motor,
            g.usuario_actual["id"],
            fecha,
        )

    except ValueError as exc:
        return error(str(exc), 400)

    except SQLAlchemyError:
        current_app.logger.error("Error al consultar la agenda.")
        return error("No fue posible consultar la agenda.", 500)

    respuesta = jsonify({
        "success": True,
        "message": "Agenda consultada correctamente",
        "data": registros,
        "meta": {
            "fecha": fecha,
            "cantidad": len(registros),
        },
    })

    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta, 200


@agenda.patch("/<int:cita_id>/estado")
@requiere_roles("personal")
def actualizar_estado_agenda(cita_id):
    if not request.is_json:
        return error("Debes enviar application/json.", 415)

    try:
        motor = current_app.extensions["db_engine"]

        resultado = cambiar_estado_agenda(
            motor,
            g.usuario_actual["id"],
            cita_id,
            request.get_json(silent=True),
        )

    except ValueError as exc:
        return error(str(exc), 400)

    except PersonalNoDisponible as exc:
        return error(str(exc), 401)

    except EstadoAgendaInvalido as exc:
        return error(str(exc), 409)

    except SQLAlchemyError:
        current_app.logger.error(
            "Error al actualizar el estado de una cita."
        )
        return error(
            "No se pudo confirmar el cambio. Consulta la agenda.",
            503,
        )

    if resultado is None:
        return error("Cita no encontrada.", 404)

    respuesta = jsonify({
        "success": True,
        "message": "Estado de cita actualizado correctamente",
        "data": resultado,
    })

    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta, 200