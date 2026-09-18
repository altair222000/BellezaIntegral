import re

from sqlalchemy import text
from werkzeug.security import generate_password_hash


def validar_registro(datos):
    if not isinstance(datos, dict):
        raise ValueError("Debes enviar un objeto JSON válido.")

    permitidos = {"nombre", "email", "telefono", "password"}

    if set(datos) - permitidos:
        raise ValueError(
            "Solo se permiten nombre, email, telefono y password."
        )

    nombre = datos.get("nombre")
    password = datos.get("password")

    if not isinstance(nombre, str):
        raise ValueError("El nombre es obligatorio.")

    nombre = nombre.strip()

    if not 1 <= len(nombre) <= 100:
        raise ValueError("El nombre debe tener entre 1 y 100 caracteres.")

    if not isinstance(password, str):
        raise ValueError("La contraseña es obligatoria.")

    if not 8 <= len(password) <= 128 or not password.strip():
        raise ValueError(
            "La contraseña debe tener entre 8 y 128 caracteres "
            "y no puede contener solamente espacios."
        )

    contactos = {}

    for campo in ("email", "telefono"):
        valor = datos.get(campo)

        if valor is not None and not isinstance(valor, str):
            raise ValueError(f"El campo {campo} debe ser texto.")

        contactos[campo] = valor.strip() or None if valor else None

    email = contactos["email"]
    telefono = contactos["telefono"]

    if not email and not telefono:
        raise ValueError("Debes proporcionar correo o teléfono.")

    if email:
        email = email.lower()

        if len(email) > 150 or not re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+", email
        ):
            raise ValueError("El correo electrónico no tiene un formato válido.")

    if telefono:
        if not re.fullmatch(r"\+?[0-9]{8,15}", telefono):
            raise ValueError(
                "El teléfono debe contener de 8 a 15 dígitos, "
                "sin espacios ni guiones; puede comenzar con +."
            )

    return {
        "nombre": nombre,
        "email": email,
        "telefono": telefono,
        "password": password,
    }


def registrar_cliente(motor, datos):
    usuario = validar_registro(datos)

    password_hash = generate_password_hash(
        usuario["password"],
        method="scrypt",
    )

    consulta = text("""
        INSERT INTO usuarios (
            nombre,
            email,
            telefono,
            password_hash,
            rol
        )
        VALUES (
            :nombre,
            :email,
            :telefono,
            :password_hash,
            'cliente'
        )
    """)

    with motor.begin() as conexion:
        resultado = conexion.execute(
            consulta,
            {
                "nombre": usuario["nombre"],
                "email": usuario["email"],
                "telefono": usuario["telefono"],
                "password_hash": password_hash,
            },
        )

        usuario_id = resultado.lastrowid

    return {
        "id": usuario_id,
        "nombre": usuario["nombre"],
        "email": usuario["email"],
        "telefono": usuario["telefono"],
        "rol": "cliente",
    }