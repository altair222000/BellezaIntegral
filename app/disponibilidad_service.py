import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text


ZONA_NEGOCIO = ZoneInfo("America/Guatemala")
PASO_MINUTOS = 15


class RecursoNoDisponible(Exception):
    pass


def validar_fecha(valor):
    if not isinstance(valor, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
        valor,
    ):
        raise ValueError("La fecha debe tener formato YYYY-MM-DD.")

    try:
        fecha = date.fromisoformat(valor)
    except ValueError:
        raise ValueError("La fecha indicada no existe.") from None

    if fecha < datetime.now(ZONA_NEGOCIO).date():
        raise ValueError("No puedes consultar una fecha pasada.")

    return fecha


def unir_fecha_hora(fecha, hora_texto):
    return datetime.combine(
        fecha,
        time.fromisoformat(hora_texto),
        tzinfo=ZONA_NEGOCIO,
    )


def calcular_disponibilidad(motor, personal_id, servicio_id, fecha_texto, *,
                           cita_excluida=None, cliente_id=None, duracion_reserva=None):
    # Los argumentos opcionales son internos: el endpoint de reprogramación
    # resuelve la cita y verifica su propietario antes de invocar esta función.
    fecha = validar_fecha(fecha_texto)

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
            raise RecursoNoDisponible(
                "El profesional no está disponible."
            )

        servicio = conexion.execute(
            text("""
                SELECT id, duracion_min
                FROM servicios
                WHERE id = :id AND activo = 1
            """),
            {"id": servicio_id},
        ).mappings().first()

        if servicio is None:
            raise RecursoNoDisponible(
                "El servicio no está disponible."
            )

        bloques = conexion.execute(
            text("""
                SELECT
                    TIME_FORMAT(hora_inicio, '%H:%i:%s') AS inicio,
                    TIME_FORMAT(hora_fin, '%H:%i:%s') AS fin
                FROM disponibilidades
                WHERE personal_id = :personal_id
                  AND dia_semana = :dia
                  AND activo = 1
                ORDER BY hora_inicio
            """),
            {
                "personal_id": personal_id,
                "dia": fecha.isoweekday(),
            },
        ).mappings().all()

        citas = conexion.execute(
            text("""
                SELECT
                    TIME_FORMAT(hora, '%H:%i:%s') AS inicio,
                    duracion_min
                FROM citas
                WHERE (personal_id = :personal_id OR cliente_id = :cliente_id)
                  AND (:cita_excluida IS NULL OR id <> :cita_excluida)
                  AND fecha = :fecha
                  AND estado <> 'cancelada'
            """),
            {
                "personal_id": personal_id,
                "fecha": fecha,
                "cliente_id": cliente_id,
                "cita_excluida": cita_excluida,
            },
        ).mappings().all()

    ocupados = []

    for cita in citas:
        inicio = unir_fecha_hora(fecha, cita["inicio"])
        fin = inicio + timedelta(minutes=cita["duracion_min"])
        ocupados.append((inicio, fin))

    ahora = datetime.now(ZONA_NEGOCIO)
    minutos = servicio["duracion_min"] if duracion_reserva is None else duracion_reserva
    duracion = timedelta(minutes=minutos)
    paso = timedelta(minutes=PASO_MINUTOS)
    horarios = []

    # Cada bloque se trata por separado para respetar descansos.
    for bloque in bloques:
        inicio = unir_fecha_hora(fecha, bloque["inicio"])
        cierre = unir_fecha_hora(fecha, bloque["fin"])

        while inicio + duracion <= cierre:
            fin = inicio + duracion

            conflicto = any(
                inicio < fin_ocupado and fin > inicio_ocupado
                for inicio_ocupado, fin_ocupado in ocupados
            )

            if inicio > ahora and not conflicto:
                horarios.append({
                    "hora_inicio": inicio.strftime("%H:%M"),
                    "hora_fin": fin.strftime("%H:%M"),
                })

            inicio += paso

    return {
        "personal_id": personal_id,
        "servicio_id": servicio_id,
        "fecha": fecha.isoformat(),
        "zona_horaria": ZONA_NEGOCIO.key,
        "duracion_min": minutos,
        "paso_minutos": PASO_MINUTOS,
        "horarios": horarios,
    }