import re
from datetime import datetime, timedelta

from sqlalchemy import text

from .disponibilidad_service import (
    PASO_MINUTOS,
    ZONA_NEGOCIO,
    unir_fecha_hora,
    validar_fecha,
)


class ConflictoCita(Exception):
    pass


class RecursoCitaNoDisponible(Exception):
    pass


def validar_cita(datos):
    if not isinstance(datos, dict):
        raise ValueError("Debes enviar un objeto JSON válido.")

    obligatorios = {"personal_id", "servicio_id", "fecha", "hora"}
    permitidos = obligatorios | {"notas"}

    if not obligatorios.issubset(datos):
        raise ValueError(
            "Debes enviar personal_id, servicio_id, fecha y hora."
        )

    if set(datos) - permitidos:
        raise ValueError("La solicitud contiene campos no permitidos.")

    for campo in ("personal_id", "servicio_id"):
        valor = datos[campo]

        if type(valor) is not int or not 1 <= valor <= 4294967295:
            raise ValueError(f"{campo} debe ser un identificador válido.")

    fecha = validar_fecha(datos["fecha"])
    hora = datos["hora"]

    if not isinstance(hora, str) or not re.fullmatch(
        r"(?:[01][0-9]|2[0-3]):[0-5][0-9]",
        hora,
    ):
        raise ValueError("La hora debe tener formato HH:MM.")

    notas = datos.get("notas")

    if notas is not None:
        if not isinstance(notas, str):
            raise ValueError("Las notas deben ser texto.")

        notas = notas.strip() or None

        if notas and len(notas) > 255:
            raise ValueError("Las notas no pueden superar 255 caracteres.")

    return {
        "personal_id": datos["personal_id"],
        "servicio_id": datos["servicio_id"],
        "fecha": fecha,
        "hora": hora,
        "notas": notas,
    }


def registrar_cita(motor, cliente_id, datos):
    cita = validar_cita(datos)
    inicio = unir_fecha_hora(cita["fecha"], cita["hora"])

    with motor.begin() as conexion:
        # Siempre bloqueamos usuarios en orden de ID.
        # Esto coordina reservas para el mismo profesional o cliente.
        usuarios = {}

        for usuario_id in sorted({cliente_id, cita["personal_id"]}):
            usuario = conexion.execute(
                text("""
                    SELECT id, rol, activo
                    FROM usuarios
                    WHERE id = :id
                    FOR UPDATE
                """),
                {"id": usuario_id},
            ).mappings().first()

            if usuario is not None:
                usuarios[usuario_id] = usuario

        cliente = usuarios.get(cliente_id)
        profesional = usuarios.get(cita["personal_id"])

        if (
            cliente is None
            or not cliente["activo"]
            or cliente["rol"] != "cliente"
        ):
            raise RecursoCitaNoDisponible(
                "El cliente no está disponible."
            )

        if (
            profesional is None
            or not profesional["activo"]
            or profesional["rol"] != "personal"
        ):
            raise RecursoCitaNoDisponible(
                "El profesional no está disponible."
            )

        servicio = conexion.execute(
            text("""
                SELECT id, duracion_min
                FROM servicios
                WHERE id = :id AND activo = 1
                FOR SHARE
            """),
            {"id": cita["servicio_id"]},
        ).mappings().first()

        if servicio is None:
            raise RecursoCitaNoDisponible(
                "El servicio no está disponible."
            )

        duracion = servicio["duracion_min"]
        fin = inicio + timedelta(minutes=duracion)

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
                FOR UPDATE
            """),
            {
                "personal_id": cita["personal_id"],
                "dia": cita["fecha"].isoweekday(),
            },
        ).mappings().all()

        dentro_del_horario = False

        for bloque in bloques:
            apertura = unir_fecha_hora(cita["fecha"], bloque["inicio"])
            cierre = unir_fecha_hora(cita["fecha"], bloque["fin"])

            segundos = (inicio - apertura).total_seconds()

            if (
                inicio >= apertura
                and fin <= cierre
                and segundos % (PASO_MINUTOS * 60) == 0
            ):
                dentro_del_horario = True
                break

        if not dentro_del_horario:
            raise ConflictoCita(
                "La cita no corresponde a un horario de atención válido."
            )

        existentes = conexion.execute(
            text("""
                SELECT
                    TIME_FORMAT(hora, '%H:%i:%s') AS inicio,
                    duracion_min
                FROM citas
                WHERE fecha = :fecha
                  AND estado <> 'cancelada'
                  AND (
                      personal_id = :personal_id
                      OR cliente_id = :cliente_id
                  )
                FOR UPDATE
            """),
            {
                "fecha": cita["fecha"],
                "personal_id": cita["personal_id"],
                "cliente_id": cliente_id,
            },
        ).mappings().all()

        for existente in existentes:
            inicio_existente = unir_fecha_hora(
                cita["fecha"],
                existente["inicio"],
            )
            fin_existente = inicio_existente + timedelta(
                minutes=existente["duracion_min"]
            )

            if inicio < fin_existente and fin > inicio_existente:
                raise ConflictoCita(
                    "El profesional o el cliente ya tiene una cita "
                    "en ese intervalo."
                )

        # Se revisa después de esperar los bloqueos.
        if inicio <= datetime.now(ZONA_NEGOCIO):
            raise ValueError("No puedes reservar una hora pasada.")

        resultado = conexion.execute(
            text("""
                INSERT INTO citas (
                    cliente_id, personal_id, servicio_id,
                    fecha, hora, duracion_min, estado, notas
                )
                VALUES (
                    :cliente_id, :personal_id, :servicio_id,
                    :fecha, :hora, :duracion_min, 'pendiente', :notas
                )
            """),
            {
                **cita,
                "cliente_id": cliente_id,
                "duracion_min": duracion,
            },
        )

        cita_id = resultado.lastrowid

    return {
        "id": cita_id,
        "cliente_id": cliente_id,
        "personal_id": cita["personal_id"],
        "servicio_id": cita["servicio_id"],
        "fecha": cita["fecha"].isoformat(),
        "hora": cita["hora"],
        "hora_fin": fin.strftime("%H:%M"),
        "duracion_min": duracion,
        "estado": "pendiente",
        "notas": cita["notas"],
    }

def listar_citas_cliente(motor, cliente_id, pagina, limite):
    consulta = text("""
        SELECT
            c.id,
            c.personal_id,
            c.servicio_id,
            s.nombre AS servicio,
            p.nombre AS profesional,
            DATE_FORMAT(c.fecha, '%Y-%m-%d') AS fecha,
            TIME_FORMAT(c.hora, '%H:%i') AS hora,
            c.duracion_min,
            c.estado,
            c.notas
        FROM citas AS c
        INNER JOIN servicios AS s
            ON s.id = c.servicio_id
        LEFT JOIN usuarios AS p
            ON p.id = c.personal_id
        WHERE c.cliente_id = :cliente_id
        ORDER BY c.fecha DESC, c.hora DESC, c.id DESC
        LIMIT :limite OFFSET :desplazamiento
    """)

    with motor.connect() as conexion:
        filas = conexion.execute(
            consulta,
            {
                "cliente_id": cliente_id,
                "limite": limite,
                "desplazamiento": (pagina - 1) * limite,
            },
        ).mappings().all()

    return [dict(fila) for fila in filas]


def cancelar_cita_cliente(motor, cliente_id, cita_id):
    with motor.begin() as conexion:
        # Coordina cambios relacionados con este cliente.
        cliente = conexion.execute(
            text("""
                SELECT id
                FROM usuarios
                WHERE id = :id
                  AND rol = 'cliente'
                  AND activo = 1
                FOR UPDATE
            """),
            {"id": cliente_id},
        ).first()

        if cliente is None:
            raise RecursoCitaNoDisponible(
                "El cliente no está disponible."
            )

        cita = conexion.execute(
            text("""
                SELECT
                    id,
                    fecha,
                    TIME_FORMAT(hora, '%H:%i:%s') AS hora,
                    estado
                FROM citas
                WHERE id = :cita_id
                  AND cliente_id = :cliente_id
                FOR UPDATE
            """),
            {
                "cita_id": cita_id,
                "cliente_id": cliente_id,
            },
        ).mappings().first()

        if cita is None:
            return None

        # Repetir una cancelación ya realizada es seguro.
        if cita["estado"] == "cancelada":
            return {
                "id": cita_id,
                "estado": "cancelada",
            }

        if cita["estado"] not in ("pendiente", "confirmada"):
            raise ConflictoCita(
                "El estado actual de la cita no permite cancelarla."
            )

        inicio = unir_fecha_hora(
            cita["fecha"],
            cita["hora"],
        )

        if inicio <= datetime.now(ZONA_NEGOCIO):
            raise ConflictoCita(
                "No puedes cancelar una cita que ya comenzó."
            )

        conexion.execute(
            text("""
                UPDATE citas
                SET estado = 'cancelada'
                WHERE id = :cita_id
                  AND cliente_id = :cliente_id
            """),
            {
                "cita_id": cita_id,
                "cliente_id": cliente_id,
            },
        )

    return {
        "id": cita_id,
        "estado": "cancelada",
    }

def reprogramar_mi_cita(motor, cliente_id, cita_id, datos):
    if not isinstance(datos, dict) or set(datos) != {"fecha", "hora"}:
        raise ValueError("Debes enviar únicamente fecha y hora.")

    fecha = validar_fecha(datos["fecha"])
    hora = datos["hora"]

    if not isinstance(hora, str) or not re.fullmatch(
        r"(?:[01][0-9]|2[0-3]):[0-5][0-9]",
        hora,
    ):
        raise ValueError("La hora debe tener formato HH:MM.")

    nuevo_inicio = unir_fecha_hora(fecha, hora)

    # Lectura inicial para identificar qué usuarios debemos bloquear.
    # Después volvemos a comprobar la cita dentro de la transacción.
    with motor.connect() as conexion:
        referencia = conexion.execute(
            text("""
                SELECT personal_id
                FROM citas
                WHERE id = :cita_id
                  AND cliente_id = :cliente_id
            """),
            {
                "cita_id": cita_id,
                "cliente_id": cliente_id,
            },
        ).mappings().first()

    if referencia is None:
        return None

    personal_id = referencia["personal_id"]

    if personal_id is None:
        raise ConflictoCita(
            "La cita necesita un profesional asignado para reprogramarse."
        )

    with motor.begin() as conexion:
        # Mismo orden de bloqueo utilizado al registrar reservas.
        usuarios = {}

        for usuario_id in sorted({cliente_id, personal_id}):
            usuario = conexion.execute(
                text("""
                    SELECT id, rol, activo
                    FROM usuarios
                    WHERE id = :id
                    FOR UPDATE
                """),
                {"id": usuario_id},
            ).mappings().first()

            if usuario is not None:
                usuarios[usuario_id] = usuario

        cliente = usuarios.get(cliente_id)
        profesional = usuarios.get(personal_id)

        if (
            cliente is None
            or not cliente["activo"]
            or cliente["rol"] != "cliente"
        ):
            raise RecursoCitaNoDisponible(
                "El cliente no está disponible."
            )

        if (
            profesional is None
            or not profesional["activo"]
            or profesional["rol"] != "personal"
        ):
            raise RecursoCitaNoDisponible(
                "El profesional no está disponible."
            )

        cita = conexion.execute(
            text("""
                SELECT
                    id, personal_id, servicio_id, fecha,
                    TIME_FORMAT(hora, '%H:%i:%s') AS hora,
                    duracion_min, estado
                FROM citas
                WHERE id = :cita_id
                  AND cliente_id = :cliente_id
                FOR UPDATE
            """),
            {
                "cita_id": cita_id,
                "cliente_id": cliente_id,
            },
        ).mappings().first()

        if cita is None:
            return None

        if cita["personal_id"] != personal_id:
            raise ConflictoCita(
                "La asignación cambió. Consulta la cita nuevamente."
            )

        if cita["estado"] not in ("pendiente", "confirmada"):
            raise ConflictoCita(
                "Solo puedes reprogramar citas pendientes o confirmadas."
            )

        inicio_original = unir_fecha_hora(cita["fecha"], cita["hora"])
        ahora = datetime.now(ZONA_NEGOCIO)

        if inicio_original <= ahora:
            raise ConflictoCita(
                "No puedes reprogramar una cita que ya comenzó."
            )

        if nuevo_inicio <= ahora:
            raise ValueError("El nuevo horario debe ser futuro.")

        # La duración histórica se conserva.
        duracion = cita["duracion_min"]
        nuevo_fin = nuevo_inicio + timedelta(minutes=duracion)

        if nuevo_inicio == inicio_original:
            return {
                "id": cita_id,
                "fecha": fecha.isoformat(),
                "hora": hora,
                "hora_fin": nuevo_fin.strftime("%H:%M"),
                "duracion_min": duracion,
                "estado": cita["estado"],
                "cambio_realizado": False,
            }

        servicio = conexion.execute(
            text("""
                SELECT id
                FROM servicios
                WHERE id = :id AND activo = 1
                FOR SHARE
            """),
            {"id": cita["servicio_id"]},
        ).first()

        if servicio is None:
            raise RecursoCitaNoDisponible(
                "El servicio no está disponible para reprogramar."
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
                FOR UPDATE
            """),
            {
                "personal_id": personal_id,
                "dia": fecha.isoweekday(),
            },
        ).mappings().all()

        horario_valido = False

        for bloque in bloques:
            apertura = unir_fecha_hora(fecha, bloque["inicio"])
            cierre = unir_fecha_hora(fecha, bloque["fin"])
            segundos = (nuevo_inicio - apertura).total_seconds()

            if (
                nuevo_inicio >= apertura
                and nuevo_fin <= cierre
                and segundos % (PASO_MINUTOS * 60) == 0
            ):
                horario_valido = True
                break

        if not horario_valido:
            raise ConflictoCita(
                "El nuevo horario no corresponde a la jornada de atención."
            )

        otras_citas = conexion.execute(
            text("""
                SELECT
                    TIME_FORMAT(hora, '%H:%i:%s') AS hora,
                    duracion_min
                FROM citas
                WHERE fecha = :fecha
                  AND id <> :cita_id
                  AND estado <> 'cancelada'
                  AND (
                      personal_id = :personal_id
                      OR cliente_id = :cliente_id
                  )
                FOR UPDATE
            """),
            {
                "fecha": fecha,
                "cita_id": cita_id,
                "personal_id": personal_id,
                "cliente_id": cliente_id,
            },
        ).mappings().all()

        for otra in otras_citas:
            inicio_ocupado = unir_fecha_hora(fecha, otra["hora"])
            fin_ocupado = inicio_ocupado + timedelta(
                minutes=otra["duracion_min"]
            )

            if nuevo_inicio < fin_ocupado and nuevo_fin > inicio_ocupado:
                raise ConflictoCita(
                    "El profesional o el cliente ya tiene una cita "
                    "en el nuevo intervalo."
                )

        # Revisamos otra vez por si hubo espera durante los bloqueos.
        ahora = datetime.now(ZONA_NEGOCIO)

        if inicio_original <= ahora or nuevo_inicio <= ahora:
            raise ConflictoCita(
                "El horario dejó de ser válido. Consulta la cita nuevamente."
            )

        conexion.execute(
            text("""
                UPDATE citas
                SET fecha = :fecha,
                    hora = :hora,
                    estado = 'pendiente'
                WHERE id = :cita_id
                  AND cliente_id = :cliente_id
            """),
            {
                "fecha": fecha,
                "hora": hora,
                "cita_id": cita_id,
                "cliente_id": cliente_id,
            },
        )

    return {
        "id": cita_id,
        "fecha": fecha.isoformat(),
        "hora": hora,
        "hora_fin": nuevo_fin.strftime("%H:%M"),
        "duracion_min": duracion,
        "estado": "pendiente",
        "cambio_realizado": True,
    }