from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from sqlalchemy.exc import SQLAlchemyError

from .permisos import requiere_roles
from .auth_service import consultar_perfil
from .servicios_service import (
    crear_servicio,
    listar_servicios,
    modificar_servicio,
    cambiar_estado_servicio,
)


servicios = Blueprint(
    "servicios",
    __name__,
    url_prefix="/api/v1/servicios",
)


def respuesta_error(mensaje, codigo):
    return jsonify({
        "success": False,
        "message": mensaje,
        "data": None,
    }), codigo


@servicios.get("")
def consultar_catalogo():
    try:
        pagina = int(request.args.get("pagina", "1"))
        limite = int(request.args.get("limite", "20"))

        if not 1 <= pagina <= 1000000 or not 1 <= limite <= 100:
            raise ValueError()

    except ValueError:
        return respuesta_error(
            "La página debe estar entre 1 y 1000000 "
            "y el límite entre 1 y 100.",
            400,
        )

    try:
        motor = current_app.extensions["db_engine"]
        verify_jwt_in_request(optional=True)
        identidad = get_jwt_identity()
        usuario_id = None
        if identidad:
            perfil = consultar_perfil(motor, identidad)
            if perfil and perfil["rol"] == "cliente":
                usuario_id = perfil["id"]

        registros = listar_servicios(
            motor,
            pagina,
            limite,
            usuario_id=usuario_id,
        )

    except SQLAlchemyError:
        current_app.logger.error("Error al consultar servicios.")
        return respuesta_error(
            "No fue posible consultar los servicios.",
            500,
        )

    return jsonify({
        "success": True,
        "message": "Catálogo consultado correctamente",
        "data": registros,
        "meta": {
            "pagina": pagina,
            "limite": limite,
            "cantidad": len(registros),
        },
    }), 200


@servicios.post("")
@requiere_roles("administrador")
def registrar_servicio():
    if not request.is_json:
        return respuesta_error(
            "Debes enviar los datos como application/json.",
            415,
        )

    datos = request.get_json(silent=True)

    try:
        motor = current_app.extensions["db_engine"]
        servicio = crear_servicio(motor, datos)

    except ValueError as error:
        return respuesta_error(str(error), 400)

    except SQLAlchemyError:
        current_app.logger.error("Error al crear un servicio.")
        return respuesta_error(
            "No fue posible crear el servicio.",
            500,
        )

    return jsonify({
        "success": True,
        "message": "Servicio creado correctamente",
        "data": servicio,
    }), 201


@servicios.put("/<int:servicio_id>")
@requiere_roles("administrador")
def actualizar_servicio(servicio_id):
    if not request.is_json:
        return respuesta_error(
            "Debes enviar los datos como application/json.",
            415,
        )

    datos = request.get_json(silent=True)

    try:
        motor = current_app.extensions["db_engine"]

        servicio = modificar_servicio(
            motor,
            servicio_id,
            datos,
        )

    except ValueError as error:
        return respuesta_error(str(error), 400)

    except SQLAlchemyError:
        current_app.logger.error("Error al modificar un servicio.")
        return respuesta_error(
            "No fue posible modificar el servicio.",
            500,
        )

    if servicio is None:
        return respuesta_error("El servicio no existe.", 404)

    return jsonify({
        "success": True,
        "message": "Servicio actualizado correctamente",
        "data": servicio,
    }), 200


@servicios.patch("/<int:servicio_id>/estado")
@requiere_roles("administrador")
def actualizar_estado_servicio(servicio_id):
    if not request.is_json:
        return respuesta_error(
            "Debes enviar los datos como application/json.",
            415,
        )

    datos = request.get_json(silent=True)

    try:
        motor = current_app.extensions["db_engine"]

        servicio = cambiar_estado_servicio(
            motor,
            servicio_id,
            datos,
        )

    except ValueError as error:
        return respuesta_error(str(error), 400)

    except SQLAlchemyError:
        current_app.logger.error(
            "Error al cambiar el estado de un servicio."
        )
        return respuesta_error(
            "No fue posible cambiar el estado del servicio.",
            500,
        )

    if servicio is None:
        return respuesta_error("El servicio no existe.", 404)

    return jsonify({
        "success": True,
        "message": "Estado del servicio actualizado correctamente",
        "data": servicio,
    }), 200