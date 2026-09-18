from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from .permisos import requiere_roles
from .citas_service import (
    ConflictoCita,
    RecursoCitaNoDisponible,
    registrar_cita,
    listar_citas_cliente,
    cancelar_cita_cliente,
    reprogramar_mi_cita,
)


citas = Blueprint(
    "citas",
    __name__,
    url_prefix="/api/v1/citas",
)


def error(mensaje, codigo):
    return jsonify({
        "success": False,
        "message": mensaje,
        "data": None,
    }), codigo


@citas.post("")
@requiere_roles("cliente")
def crear_cita():
    if not request.is_json:
        return error("Debes enviar application/json.", 415)

    try:
        motor = current_app.extensions["db_engine"]

        cita = registrar_cita(
            motor,
            g.usuario_actual["id"],
            request.get_json(silent=True),
        )

    except ValueError as exc:
        return error(str(exc), 400)

    except RecursoCitaNoDisponible as exc:
        return error(str(exc), 404)

    except ConflictoCita as exc:
        return error(str(exc), 409)

    except OperationalError:
        current_app.logger.error(
            "Fallo operativo durante el registro de una cita."
        )
        return error(
            "No se pudo confirmar el resultado de la reserva. "
            "Consulta tus citas antes de reintentar.",
            503,
        )

    except SQLAlchemyError:
        current_app.logger.error("Error al registrar una cita.")
        return error("No fue posible registrar la cita.", 500)

    return jsonify({
        "success": True,
        "message": "Cita registrada correctamente",
        "data": cita,
    }), 201
@citas.get("/mias")
@requiere_roles("cliente")
def consultar_mis_citas():
    try:
        pagina = int(request.args.get("pagina", "1"))
        limite = int(request.args.get("limite", "20"))

        if not 1 <= pagina <= 1000000 or not 1 <= limite <= 100:
            raise ValueError()

    except ValueError:
        return error(
            "La página debe estar entre 1 y 1000000 "
            "y el límite entre 1 y 100.",
            400,
        )

    try:
        motor = current_app.extensions["db_engine"]

        registros = listar_citas_cliente(
            motor,
            g.usuario_actual["id"],
            pagina,
            limite,
        )

    except SQLAlchemyError:
        current_app.logger.error(
            "Error al consultar las citas del cliente."
        )
        return error("No fue posible consultar tus citas.", 500)

    respuesta = jsonify({
        "success": True,
        "message": "Citas consultadas correctamente",
        "data": registros,
        "meta": {
            "pagina": pagina,
            "limite": limite,
            "cantidad": len(registros),
        },
    })

    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta, 200


@citas.patch("/<int:cita_id>/cancelar")
@requiere_roles("cliente")
def cancelar_mi_cita(cita_id):
    try:
        motor = current_app.extensions["db_engine"]

        resultado = cancelar_cita_cliente(
            motor,
            g.usuario_actual["id"],
            cita_id,
        )

    except RecursoCitaNoDisponible as exc:
        return error(str(exc), 401)

    except ConflictoCita as exc:
        return error(str(exc), 409)

    except SQLAlchemyError:
        current_app.logger.error("Error al cancelar una cita.")
        return error(
            "No se pudo confirmar la cancelación. Consulta tus citas.",
            500,
        )

    if resultado is None:
        return error("Cita no encontrada.", 404)

    respuesta = jsonify({
        "success": True,
        "message": "La cita está cancelada",
        "data": resultado,
    })

    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta, 200
@citas.patch("/<int:cita_id>/reprogramar")
@requiere_roles("cliente")
def reprogramar_cita(cita_id):
    if not request.is_json:
        return error("Debes enviar application/json.", 415)

    try:
        motor = current_app.extensions["db_engine"]

        resultado = reprogramar_mi_cita(
            motor,
            g.usuario_actual["id"],
            cita_id,
            request.get_json(silent=True),
        )

    except ValueError as exc:
        return error(str(exc), 400)

    except RecursoCitaNoDisponible as exc:
        return error(str(exc), 404)

    except ConflictoCita as exc:
        return error(str(exc), 409)

    except SQLAlchemyError:
        current_app.logger.error("Error al reprogramar una cita.")
        return error(
            "No se pudo confirmar la reprogramación. "
            "Consulta tus citas antes de reintentar.",
            503,
        )

    if resultado is None:
        return error("Cita no encontrada.", 404)

    mensaje = (
        "Cita reprogramada correctamente"
        if resultado["cambio_realizado"]
        else "La cita ya tiene ese horario"
    )

    respuesta = jsonify({
        "success": True,
        "message": mensaje,
        "data": resultado,
    })

    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta, 200

# Consulta privada para el selector de reprogramación del website y móvil.
from .api_common import endpoint, response
from .reprogramacion_service import horarios_para_reprogramar


@citas.get("/<int:cita_id>/disponibilidad")
@requiere_roles("cliente")
@endpoint
def disponibilidad_de_mi_cita(cita_id):
    return response(horarios_para_reprogramar(
        current_app.extensions["db_engine"], g.usuario_actual["id"],
        cita_id, request.args,
    ), message="Horarios para reprogramar consultados correctamente")
