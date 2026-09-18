import re

from sqlalchemy import text


class HorarioEnConflicto(Exception):
    pass


def listar_personal(motor):
    with motor.connect() as conexion:
        filas = conexion.execute(text("""
            SELECT id, nombre
            FROM usuarios
            WHERE rol = 'personal' AND activo = 1
            ORDER BY nombre, id
        """)).mappings().all()

    return [dict(fila) for fila in filas]


def consultar_horarios(motor, personal_id):
    with motor.connect() as conexion:
        profesional = conexion.execute(
            text("""
                SELECT id
                FROM usuarios
                WHERE id = :id
                  AND rol = 'personal'
                  AND activo = 1
            """),
            {"id": personal_id},
        ).first()

        if profesional is None:
            return None

        filas = conexion.execute(
            text("""
                SELECT id, personal_id, dia_semana,
                       TIME_FORMAT(hora_inicio, '%H:%i') AS hora_inicio,
                       TIME_FORMAT(hora_fin, '%H:%i') AS hora_fin
                FROM disponibilidades
                WHERE personal_id = :id AND activo = 1
                ORDER BY dia_semana, hora_inicio, id
            """),
            {"id": personal_id},
        ).mappings().all()

    return [dict(fila) for fila in filas]


def validar_horario(datos):
    if not isinstance(datos, dict):
        raise ValueError("Debes enviar un objeto JSON válido.")

    campos = {"dia_semana", "hora_inicio", "hora_fin"}

    if set(datos) != campos:
        raise ValueError(
            "Envía únicamente dia_semana, hora_inicio y hora_fin."
        )

    dia = datos["dia_semana"]

    if type(dia) is not int or not 1 <= dia <= 7:
        raise ValueError(
            "dia_semana debe ser un entero de 1 (lunes) a 7 (domingo)."
        )

    for campo in ("hora_inicio", "hora_fin"):
        valor = datos[campo]

        if not isinstance(valor, str) or not re.fullmatch(
            r"(?:[01][0-9]|2[0-3]):[0-5][0-9]",
            valor,
        ):
            raise ValueError(
                f"{campo} debe usar el formato HH:MM, por ejemplo 09:00."
            )

    if datos["hora_fin"] <= datos["hora_inicio"]:
        raise ValueError(
            "La hora final debe ser posterior a la inicial."
        )

    return {
        "dia_semana": dia,
        "hora_inicio": datos["hora_inicio"],
        "hora_fin": datos["hora_fin"],
    }


def registrar_horario(motor, personal_id, datos):
    horario = validar_horario(datos)

    with motor.begin() as conexion:
        # Serializa las altas de horarios para este profesional.
        profesional = conexion.execute(
            text("""
                SELECT id
                FROM usuarios
                WHERE id = :id
                  AND rol = 'personal'
                  AND activo = 1
                FOR UPDATE
            """),
            {"id": personal_id},
        ).first()

        if profesional is None:
            return None

        parametros = {
            "personal_id": personal_id,
            **horario,
        }

        conflicto = conexion.execute(
            text("""
                SELECT id
                FROM disponibilidades
                WHERE personal_id = :personal_id
                  AND dia_semana = :dia_semana
                  AND activo = 1
                  AND hora_inicio < :hora_fin
                  AND hora_fin > :hora_inicio
                LIMIT 1
                FOR UPDATE
            """),
            parametros,
        ).first()

        if conflicto is not None:
            raise HorarioEnConflicto(
                "El bloque se superpone con un horario existente."
            )

        resultado = conexion.execute(
            text("""
                INSERT INTO disponibilidades (
                    personal_id, dia_semana, hora_inicio, hora_fin
                )
                VALUES (
                    :personal_id, :dia_semana, :hora_inicio, :hora_fin
                )
            """),
            parametros,
        )

        horario_id = resultado.lastrowid

    return {
        "id": horario_id,
        **parametros,
        "activo": True,
    }