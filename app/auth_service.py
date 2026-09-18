import secrets

from sqlalchemy import text
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)


HASH_COMPROBACION = generate_password_hash(
    secrets.token_urlsafe(32),
    method="scrypt",
)


def autenticar_usuario(motor, datos):
    if not isinstance(datos, dict):
        raise ValueError("Debes enviar un objeto JSON válido.")

    if set(datos) - {"identificador", "password"}:
        raise ValueError(
            "Solo se permiten identificador y password."
        )

    identificador = datos.get("identificador")
    password = datos.get("password")

    if not isinstance(identificador, str):
        raise ValueError("El correo o teléfono es obligatorio.")

    identificador = identificador.strip()

    if not 1 <= len(identificador) <= 150:
        raise ValueError("El correo o teléfono no es válido.")

    if (
        not isinstance(password, str)
        or not 1 <= len(password) <= 128
    ):
        raise ValueError(
            "La contraseña es obligatoria o excede el límite."
        )

    if "@" in identificador:
        identificador = identificador.lower()

        consulta = text("""
            SELECT id, nombre, email, telefono,
                   password_hash, rol, activo
            FROM usuarios
            WHERE email = :identificador FOR UPDATE
        """)
    else:
        consulta = text("""
            SELECT id, nombre, email, telefono,
                   password_hash, rol, activo
            FROM usuarios
            WHERE telefono = :identificador FOR UPDATE
        """)

    with motor.begin() as conexion:
        usuario = conexion.execute(consulta, {"identificador": identificador}).mappings().first()
        hash_guardado = usuario["password_hash"] if usuario else HASH_COMPROBACION
        password_correcto = check_password_hash(hash_guardado, password)
        if not usuario or not password_correcto or not usuario["activo"]:
            return None
        version = conexion.execute(text(
            "SELECT version FROM sesiones_usuario WHERE usuario_id=:id"
        ), {"id": usuario["id"]}).scalar() or 0
        return {
            "id": usuario["id"], "nombre": usuario["nombre"],
            "email": usuario["email"], "telefono": usuario["telefono"],
            "rol": usuario["rol"], "_version_sesion": version,
        }


def consultar_perfil(motor, identidad):
    if (
        not isinstance(identidad, str)
        or not identidad.isdecimal()
    ):
        return None

    usuario_id = int(identidad)

    if not 1 <= usuario_id <= 4294967295:
        return None

    consulta = text("""
        SELECT id, nombre, email, telefono, rol, puntos
        FROM usuarios
        WHERE id = :id AND activo = 1
    """)

    with motor.connect() as conexion:
        usuario = conexion.execute(
            consulta,
            {"id": usuario_id},
        ).mappings().first()

    return dict(usuario) if usuario else None