import re
from decimal import Decimal

from sqlalchemy import text

from .suscripciones_service import (
    descuento_servicios_activo,
    precio_con_descuento,
)


def validar_servicio(datos):
    if not isinstance(datos, dict):
        raise ValueError("Debes enviar un objeto JSON válido.")

    permitidos = {
        "nombre",
        "descripcion",
        "categoria",
        "duracion_min",
        "precio",
        "imagen",
    }

    if set(datos) - permitidos:
        raise ValueError("La solicitud contiene campos no permitidos.")

    resultado = {}

    for campo, limite in (("nombre", 100), ("categoria", 50)):
        valor = datos.get(campo)

        if not isinstance(valor, str):
            raise ValueError(f"El campo {campo} es obligatorio.")

        valor = valor.strip()

        if not 1 <= len(valor) <= limite:
            raise ValueError(
                f"El campo {campo} debe tener entre 1 y {limite} caracteres."
            )

        resultado[campo] = valor

    descripcion = datos.get("descripcion")

    if descripcion is not None:
        if not isinstance(descripcion, str):
            raise ValueError("La descripción debe ser texto.")

        descripcion = descripcion.strip() or None

        if descripcion and len(descripcion.encode("utf-8")) > 65535:
            raise ValueError("La descripción supera el tamaño permitido.")

    resultado["descripcion"] = descripcion

    duracion = datos.get("duracion_min")

    # bool también es un subtipo de int en Python:
    # utilizamos type para rechazar true y false.
    if type(duracion) is not int or not 1 <= duracion <= 65535:
        raise ValueError(
            "La duración debe ser un número entero de 1 a 65535 minutos."
        )

    resultado["duracion_min"] = duracion

    # El precio se recibe como texto para conservar precisión decimal.
    precio = datos.get("precio")

    if not isinstance(precio, str):
        raise ValueError('Envía el precio como texto; por ejemplo, "125.00".')

    precio = precio.strip()

    if not re.fullmatch(r"[0-9]{1,8}(?:\.[0-9]{1,2})?", precio):
        raise ValueError(
            "El precio debe ser positivo o cero, con máximo dos decimales "
            "y sin superar 99999999.99."
        )

    resultado["precio"] = Decimal(precio).quantize(Decimal("0.01"))

    imagen = datos.get("imagen")

    if imagen is not None:
        if not isinstance(imagen, str):
            raise ValueError("La imagen debe ser una referencia de texto.")

        imagen = imagen.strip() or None

        if imagen and len(imagen) > 255:
            raise ValueError("La referencia de imagen supera 255 caracteres.")

    resultado["imagen"] = imagen

    return resultado


def crear_servicio(motor, datos):
    servicio = validar_servicio(datos)

    consulta = text("""
        INSERT INTO servicios (
            nombre, descripcion, categoria,
            duracion_min, precio, imagen
        )
        VALUES (
            :nombre, :descripcion, :categoria,
            :duracion_min, :precio, :imagen
        )
    """)

    with motor.begin() as conexion:
        resultado = conexion.execute(consulta, servicio)
        servicio_id = resultado.lastrowid

    return {
        "id": servicio_id,
        **servicio,
        "precio": format(servicio["precio"], ".2f"),
        "activo": True,
    }


def listar_servicios(motor, pagina, limite, usuario_id=None):
    desplazamiento = (pagina - 1) * limite

    consulta = text("""
        SELECT id, nombre, descripcion, categoria,
               duracion_min, precio, activo, imagen
        FROM servicios
        WHERE activo = 1
        ORDER BY id
        LIMIT :limite OFFSET :desplazamiento
    """)

    with motor.connect() as conexion:
        descuento = descuento_servicios_activo(
            conexion,
            usuario_id,
        )
        filas = conexion.execute(
            consulta,
            {
                "limite": limite,
                "desplazamiento": desplazamiento,
            },
        ).mappings().all()

    servicios = []

    for fila in filas:
        servicio = dict(fila)
        precio_original = servicio["precio"]
        precio_final = precio_con_descuento(
            precio_original,
            descuento,
        )
        servicio["precio_original"] = format(
            precio_original,
            ".2f",
        )
        servicio["precio"] = format(precio_final, ".2f")
        servicio["descuento_suscripcion"] = descuento
        servicio["activo"] = bool(servicio["activo"])
        servicios.append(servicio)

    return servicios

def modificar_servicio(motor, servicio_id, datos):
    servicio = validar_servicio(datos)

    with motor.begin() as conexion:
        existente = conexion.execute(
            text("""
                SELECT id, activo
                FROM servicios
                WHERE id = :id
                FOR UPDATE
            """),
            {"id": servicio_id},
        ).mappings().first()

        if existente is None:
            return None

        conexion.execute(
            text("""
                UPDATE servicios
                SET nombre = :nombre,
                    descripcion = :descripcion,
                    categoria = :categoria,
                    duracion_min = :duracion_min,
                    precio = :precio,
                    imagen = :imagen
                WHERE id = :id
            """),
            {
                **servicio,
                "id": servicio_id,
            },
        )

        activo = bool(existente["activo"])

    return {
        "id": servicio_id,
        **servicio,
        "precio": format(servicio["precio"], ".2f"),
        "activo": activo,
    }


def cambiar_estado_servicio(motor, servicio_id, datos):
    if not isinstance(datos, dict):
        raise ValueError("Debes enviar un objeto JSON válido.")

    if set(datos) != {"activo"}:
        raise ValueError("Debes enviar únicamente el campo activo.")

    activo = datos["activo"]

    if type(activo) is not bool:
        raise ValueError("El campo activo debe ser true o false.")

    with motor.begin() as conexion:
        existente = conexion.execute(
            text("""
                SELECT id
                FROM servicios
                WHERE id = :id
                FOR UPDATE
            """),
            {"id": servicio_id},
        ).first()

        if existente is None:
            return None

        conexion.execute(
            text("""
                UPDATE servicios
                SET activo = :activo
                WHERE id = :id
            """),
            {
                "id": servicio_id,
                "activo": int(activo),
            },
        )

    return {
        "id": servicio_id,
        "activo": activo,
    }