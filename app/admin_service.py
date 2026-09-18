from sqlalchemy import text

from .agenda_service import validar_fecha_agenda


ESTADOS_CITA = {
    "pendiente",
    "confirmada",
    "completada",
    "cancelada",
}


def validar_filtros_citas(argumentos):
    permitidos = {
        "fecha",
        "personal_id",
        "estado",
        "pagina",
        "limite",
    }

    if set(argumentos) - permitidos:
        raise ValueError("La consulta contiene filtros no permitidos.")

    for campo in argumentos:
        if len(argumentos.getlist(campo)) != 1:
            raise ValueError(f"El filtro {campo} no puede repetirse.")

    filtros = {}

    if "fecha" in argumentos:
        filtros["fecha"] = validar_fecha_agenda(argumentos["fecha"])

    if "personal_id" in argumentos:
        try:
            personal_id = int(argumentos["personal_id"])
        except ValueError:
            raise ValueError("personal_id debe ser un número entero.") from None

        if not 1 <= personal_id <= 4294967295:
            raise ValueError("personal_id está fuera del rango permitido.")

        filtros["personal_id"] = personal_id

    if "estado" in argumentos:
        estado = argumentos["estado"]

        if estado not in ESTADOS_CITA:
            raise ValueError(
                "El estado debe ser pendiente, confirmada, "
                "completada o cancelada."
            )

        filtros["estado"] = estado

    try:
        pagina = int(argumentos.get("pagina", "1"))
        limite = int(argumentos.get("limite", "20"))
    except ValueError:
        raise ValueError("pagina y limite deben ser números enteros.") from None

    if not 1 <= pagina <= 1000000:
        raise ValueError("La página debe estar entre 1 y 1000000.")

    if not 1 <= limite <= 100:
        raise ValueError("El límite debe estar entre 1 y 100.")

    return filtros, pagina, limite


def consultar_citas_administrativas(motor, filtros, pagina, limite):
    condiciones = []
    parametros = {}

    if "fecha" in filtros:
        condiciones.append("c.fecha = :fecha")
        parametros["fecha"] = filtros["fecha"]

    if "personal_id" in filtros:
        condiciones.append("c.personal_id = :personal_id")
        parametros["personal_id"] = filtros["personal_id"]

    if "estado" in filtros:
        condiciones.append("c.estado = :estado")
        parametros["estado"] = filtros["estado"]

    # Solo concatenamos fragmentos SQL definidos por nosotros.
    # Los valores recibidos se envían como parámetros.
    where = " AND ".join(condiciones) if condiciones else "1 = 1"

    consulta_total = text(
        "SELECT COUNT(*) FROM citas AS c WHERE " + where
    )

    consulta = text("""
        SELECT
            c.id,
            c.cliente_id,
            cliente.nombre AS cliente,
            c.personal_id,
            profesional.nombre AS profesional,
            c.servicio_id,
            s.nombre AS servicio,
            DATE_FORMAT(c.fecha, '%Y-%m-%d') AS fecha,
            TIME_FORMAT(c.hora, '%H:%i') AS hora,
            c.duracion_min,
            c.estado,
            c.notas
        FROM citas AS c
        INNER JOIN usuarios AS cliente
            ON cliente.id = c.cliente_id
        LEFT JOIN usuarios AS profesional
            ON profesional.id = c.personal_id
        INNER JOIN servicios AS s
            ON s.id = c.servicio_id
        WHERE """ + where + """
        ORDER BY c.fecha DESC, c.hora DESC, c.id DESC
        LIMIT :limite OFFSET :desplazamiento
    """)

    with motor.connect() as conexion:
        total = conexion.execute(
            consulta_total,
            parametros,
        ).scalar_one()

        filas = conexion.execute(
            consulta,
            {
                **parametros,
                "limite": limite,
                "desplazamiento": (pagina - 1) * limite,
            },
        ).mappings().all()

    return {
        "registros": [dict(fila) for fila in filas],
        "total": total,
    }