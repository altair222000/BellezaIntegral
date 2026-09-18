from flask import Blueprint, current_app, g, jsonify, request
from .permisos import requiere_roles
from sqlalchemy.exc import SQLAlchemyError

from .admin_service import (
    validar_filtros_citas,
    consultar_citas_administrativas,
)

admin = Blueprint(
    "admin",
    __name__,
    url_prefix="/api/v1/admin",
)


@admin.get("/verificar")
@requiere_roles("administrador")
def verificar_administrador():
    respuesta = jsonify({
        "success": True,
        "message": "Acceso administrativo autorizado",
        "data": {
            "id": g.usuario_actual["id"],
            "nombre": g.usuario_actual["nombre"],
            "rol": g.usuario_actual["rol"],
        },
    })

    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta, 200
@admin.get("/citas")
@requiere_roles("administrador")
def consultar_citas():
    try:
        filtros, pagina, limite = validar_filtros_citas(request.args)

        motor = current_app.extensions["db_engine"]

        resultado = consultar_citas_administrativas(
            motor,
            filtros,
            pagina,
            limite,
        )

    except ValueError as exc:
        return jsonify({
            "success": False,
            "message": str(exc),
            "data": None,
        }), 400

    except SQLAlchemyError:
        current_app.logger.error(
            "Error al consultar las citas administrativas."
        )
        return jsonify({
            "success": False,
            "message": "No fue posible consultar las citas.",
            "data": None,
        }), 500

    total = resultado["total"]

    respuesta = jsonify({
        "success": True,
        "message": "Citas administrativas consultadas correctamente",
        "data": resultado["registros"],
        "meta": {
            "pagina": pagina,
            "limite": limite,
            "cantidad": len(resultado["registros"]),
            "total": total,
            "paginas": (total + limite - 1) // limite,
        },
    })

    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta, 200

# BEGIN BELLEZA ADMIN USUARIOS V1
from sqlalchemy.exc import IntegrityError
from .admin_usuarios_service import (
    AdministradorNoDisponible, ConflictoUsuario, validar_filtros_usuarios,
    listar_usuarios, crear_personal, cambiar_estado_usuario,
)


def _respuesta_usuarios(mensaje, datos=None, codigo=200, meta=None):
    contenido = {"success": codigo < 400, "message": mensaje, "data": datos}
    if meta is not None:
        contenido["meta"] = meta
    respuesta = jsonify(contenido)
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta, codigo


@admin.get("/usuarios")
@requiere_roles("administrador")
def consultar_usuarios():
    try:
        filtros, pagina, limite = validar_filtros_usuarios(request.args)
        resultado = listar_usuarios(current_app.extensions["db_engine"], filtros, pagina, limite)
    except ValueError as exc:
        return _respuesta_usuarios(str(exc), codigo=400)
    except SQLAlchemyError:
        current_app.logger.error("Error al consultar usuarios administrativos.")
        return _respuesta_usuarios("No fue posible consultar usuarios.", codigo=503)
    total = resultado["total"]
    return _respuesta_usuarios("Usuarios consultados correctamente", resultado["registros"], meta={
        "pagina": pagina, "limite": limite, "cantidad": len(resultado["registros"]),
        "total": total, "paginas": (total + limite - 1) // limite,
    })


@admin.post("/personal")
@requiere_roles("administrador")
def registrar_personal():
    if not request.is_json:
        return _respuesta_usuarios("Debes enviar los datos como application/json.", codigo=415)
    try:
        usuario = crear_personal(current_app.extensions["db_engine"],
                                 g.usuario_actual["id"], request.get_json(silent=True))
    except ValueError as exc:
        return _respuesta_usuarios(str(exc), codigo=400)
    except AdministradorNoDisponible as exc:
        return _respuesta_usuarios(str(exc), codigo=401)
    except IntegrityError as exc:
        argumentos = getattr(exc.orig, "args", ())
        if argumentos and argumentos[0] == 1062:
            return _respuesta_usuarios("El correo o teléfono ya está en uso.", codigo=409)
        current_app.logger.error("Restricción de base de datos al crear personal.")
        return _respuesta_usuarios("No fue posible registrar al personal.", codigo=500)
    except SQLAlchemyError:
        current_app.logger.error("Error de base de datos al crear personal.")
        return _respuesta_usuarios("No fue posible confirmar el registro. Consulta usuarios antes de reintentar.", codigo=503)
    return _respuesta_usuarios("Personal registrado correctamente", usuario, 201)


@admin.patch("/usuarios/<int:usuario_id>/estado")
@requiere_roles("administrador")
def actualizar_estado_usuario(usuario_id):
    if not request.is_json:
        return _respuesta_usuarios("Debes enviar los datos como application/json.", codigo=415)
    try:
        usuario = cambiar_estado_usuario(current_app.extensions["db_engine"],
            g.usuario_actual["id"], usuario_id, request.get_json(silent=True))
    except ValueError as exc:
        return _respuesta_usuarios(str(exc), codigo=400)
    except ConflictoUsuario as exc:
        return _respuesta_usuarios(str(exc), codigo=409)
    except AdministradorNoDisponible as exc:
        return _respuesta_usuarios(str(exc), codigo=401)
    except SQLAlchemyError:
        current_app.logger.error("Error de base de datos al cambiar estado de usuario.")
        return _respuesta_usuarios("No fue posible confirmar el cambio. Consulta el usuario antes de reintentar.", codigo=503)
    if usuario is None:
        return _respuesta_usuarios("Usuario no encontrado.", codigo=404)
    return _respuesta_usuarios("Estado del usuario actualizado correctamente", usuario)
# END BELLEZA ADMIN USUARIOS V1
