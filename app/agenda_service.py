import re
from datetime import date, datetime, timedelta

from sqlalchemy import text

from .disponibilidad_service import ZONA_NEGOCIO, unir_fecha_hora


class EstadoAgendaInvalido(Exception):
    pass


class PersonalNoDisponible(Exception):
    pass


def validar_fecha_agenda(valor):
    if not isinstance(valor, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
        valor,
    ):
        raise ValueError("La fecha debe tener formato YYYY-MM-DD.")

    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ValueError("La fecha indicada no existe.") from None


def consultar_agenda(motor, personal_id, fecha_texto):
    fecha = validar_fecha_agenda(fecha_texto)

    with motor.connect() as conexion:
        filas = conexion.execute(
            text("""
                SELECT
                    c.id,
                    c.cliente_id,
                    u.nombre AS cliente,
                    c.servicio_id,
                    s.nombre AS servicio,
                    DATE_FORMAT(c.fecha, '%Y-%m-%d') AS fecha,
                    TIME_FORMAT(c.hora, '%H:%i') AS hora,
                    c.duracion_min,
                    c.estado,
                    c.notas
                FROM citas AS c
                INNER JOIN usuarios AS u ON u.id = c.cliente_id
                INNER JOIN servicios AS s ON s.id = c.servicio_id
                WHERE c.personal_id = :personal_id
                  AND c.fecha = :fecha
                ORDER BY c.hora, c.id
            """),
            {
                "personal_id": personal_id,
                "fecha": fecha,
            },
        ).mappings().all()

    return [dict(fila) for fila in filas]


def cambiar_estado_agenda(motor, personal_id, cita_id, datos):
    if not isinstance(datos, dict) or set(datos) != {"estado"}:
        raise ValueError("Debes enviar únicamente el campo estado.")

    nuevo_estado = datos["estado"]

    if (
        not isinstance(nuevo_estado, str)
        or nuevo_estado not in ("confirmada", "completada")
    ):
        raise ValueError(
            "El estado debe ser confirmada o completada."
        )

    with motor.begin() as conexion:
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
            raise PersonalNoDisponible(
                "La cuenta de personal no está disponible."
            )

        cita = conexion.execute(
            text("""
                SELECT
                    id,
                    fecha,
                    TIME_FORMAT(hora, '%H:%i:%s') AS hora,
                    duracion_min,
                    estado
                FROM citas
                WHERE id = :cita_id
                  AND personal_id = :personal_id
                FOR UPDATE
            """),
            {
                "cita_id": cita_id,
                "personal_id": personal_id,
            },
        ).mappings().first()

        if cita is None:
            return None

        estado_actual = cita["estado"]

        # Una repetición del mismo cambio no altera nuevamente la cita.
        if estado_actual == nuevo_estado:
            return {
                "id": cita_id,
                "estado": estado_actual,
            }

        inicio = unir_fecha_hora(cita["fecha"], cita["hora"])
        fin = inicio + timedelta(minutes=cita["duracion_min"])
        ahora = datetime.now(ZONA_NEGOCIO)

        if nuevo_estado == "confirmada":
            if estado_actual != "pendiente":
                raise EstadoAgendaInvalido(
                    "Solo puedes confirmar una cita pendiente."
                )

            if inicio <= ahora:
                raise EstadoAgendaInvalido(
                    "No puedes confirmar una cita que ya comenzó."
                )

        if nuevo_estado == "completada":
            if estado_actual != "confirmada":
                raise EstadoAgendaInvalido(
                    "Solo puedes completar una cita confirmada."
                )

            if ahora < fin:
                raise EstadoAgendaInvalido(
                    "No puedes completar la cita antes de su hora final."
                )

        conexion.execute(
            text("""
                UPDATE citas
                SET estado = :estado
                WHERE id = :cita_id
                  AND personal_id = :personal_id
            """),
            {
                "estado": nuevo_estado,
                "cita_id": cita_id,
                "personal_id": personal_id,
            },
        )

    return {
        "id": cita_id,
        "estado": nuevo_estado,
    }