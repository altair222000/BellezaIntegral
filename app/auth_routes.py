from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .usuarios_service import registrar_cliente
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)

from .auth_service import autenticar_usuario, consultar_perfil


auth = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/v1/auth",
)


def respuesta_error(mensaje, codigo):
    return jsonify({
        "success": False,
        "message": mensaje,
        "data": None,
    }), codigo


@auth.post("/registro")
def registro():
    if not request.is_json:
        return respuesta_error(
            "Debes enviar los datos como application/json.",
            415,
        )

    datos = request.get_json(silent=True)

    try:
        motor = current_app.extensions["db_engine"]
        usuario = registrar_cliente(motor, datos)

    except ValueError as error:
        return respuesta_error(str(error), 400)

    except IntegrityError as error:
        argumentos = getattr(error.orig, "args", ())
        codigo_mysql = argumentos[0] if argumentos else None

        if codigo_mysql == 1062:
            return respuesta_error(
                "No se pudo registrar: el correo o teléfono ya está en uso.",
                409,
            )

        current_app.logger.error(
            "El registro incumplió una restricción de la base de datos."
        )

        return respuesta_error(
            "No fue posible registrar al cliente.",
            500,
        )

    except SQLAlchemyError:
        current_app.logger.error(
            "Error de base de datos durante el registro."
        )

        return respuesta_error(
            "No fue posible registrar al cliente.",
            500,
        )

    return jsonify({
        "success": True,
        "message": "Cliente registrado correctamente",
        "data": usuario,
    }), 201

@auth.post("/login")
def login():
    if not request.is_json:
        return respuesta_error(
            "Debes enviar los datos como application/json.",
            415,
        )

    datos = request.get_json(silent=True)

    try:
        motor = current_app.extensions["db_engine"]
        usuario = autenticar_usuario(motor, datos)

    except ValueError as error:
        return respuesta_error(str(error), 400)

    except SQLAlchemyError:
        current_app.logger.error(
            "Error de base de datos durante el inicio de sesión."
        )
        return respuesta_error(
            "No fue posible iniciar sesión.",
            500,
        )

    if usuario is None:
        return respuesta_error(
            "Credenciales incorrectas o cuenta no disponible.",
            401,
        )

    version = usuario.pop("_version_sesion")
    token = create_access_token(identity=str(usuario["id"]), additional_claims={"version":version})

    respuesta = jsonify({
        "success": True,
        "message": "Inicio de sesión correcto",
        "data": {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": int(
                current_app.config[
                    "JWT_ACCESS_TOKEN_EXPIRES"
                ].total_seconds()
            ),
            "usuario": usuario,
        },
    })

    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta, 200


@auth.get("/perfil")
@jwt_required()
def perfil():
    try:
        motor = current_app.extensions["db_engine"]

        usuario = consultar_perfil(
            motor,
            get_jwt_identity(),
        )

    except SQLAlchemyError:
        current_app.logger.error(
            "Error de base de datos durante la consulta del perfil."
        )
        return respuesta_error(
            "No fue posible consultar el perfil.",
            500,
        )

    if usuario is None:
        return respuesta_error(
            "La cuenta no está disponible.",
            401,
        )

    respuesta = jsonify({
        "success": True,
        "message": "Perfil consultado correctamente",
        "data": usuario,
    })

    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta, 200