"""Administración de cuentas; reutiliza la validación del registro público."""
from sqlalchemy import text
from werkzeug.security import generate_password_hash
from .usuarios_service import validar_registro


class ConflictoUsuario(Exception):
    pass


class AdministradorNoDisponible(Exception):
    pass


def validar_filtros_usuarios(argumentos):
    if set(argumentos) - {"rol", "activo", "pagina", "limite"}:
        raise ValueError("La consulta contiene filtros no permitidos.")
    for campo in argumentos:
        if len(argumentos.getlist(campo)) != 1:
            raise ValueError(f"El filtro {campo} no puede repetirse.")
    filtros = {}
    if "rol" in argumentos:
        if argumentos["rol"] not in {"administrador", "personal", "cliente"}:
            raise ValueError("El rol no es válido.")
        filtros["rol"] = argumentos["rol"]
    if "activo" in argumentos:
        if argumentos["activo"] not in {"true", "false"}:
            raise ValueError("activo debe ser true o false.")
        filtros["activo"] = int(argumentos["activo"] == "true")
    try:
        pagina = int(argumentos.get("pagina", "1"))
        limite = int(argumentos.get("limite", "20"))
    except ValueError:
        raise ValueError("pagina y limite deben ser enteros.") from None
    if not 1 <= pagina <= 1000000 or not 1 <= limite <= 100:
        raise ValueError("pagina debe estar entre 1 y 1000000; limite entre 1 y 100.")
    return filtros, pagina, limite


def listar_usuarios(motor, filtros, pagina, limite):
    # Las columnas y fragmentos son constantes; todos los valores se parametrizan.
    condiciones = []
    for campo in ("rol", "activo"):
        if campo in filtros:
            condiciones.append(f"{campo} = :{campo}")
    where = " AND ".join(condiciones) or "1 = 1"
    with motor.connect() as conexion:
        total = conexion.execute(text("SELECT COUNT(*) FROM usuarios WHERE " + where), filtros).scalar_one()
        filas = conexion.execute(text("""
            SELECT id, nombre, email, telefono, rol, puntos, activo,
                   DATE_FORMAT(fecha_registro, '%Y-%m-%d %H:%i:%s') AS fecha_registro
            FROM usuarios WHERE """ + where + " ORDER BY id LIMIT :limite OFFSET :offset"),
            {**filtros, "limite": limite, "offset": (pagina - 1) * limite}).mappings().all()
    return {"total": total, "registros": [{**dict(f), "activo": bool(f["activo"])} for f in filas]}


def _validar_administrador(fila):
    if fila is None or not fila["activo"] or fila["rol"] != "administrador":
        raise AdministradorNoDisponible("La cuenta administradora no está disponible.")


def crear_personal(motor, administrador_id, datos):
    usuario = validar_registro(datos)
    password_hash = generate_password_hash(usuario["password"], method="scrypt")
    with motor.begin() as conexion:
        administrador = conexion.execute(text(
            "SELECT id, rol, activo FROM usuarios WHERE id = :id FOR UPDATE"
        ), {"id": administrador_id}).mappings().first()
        _validar_administrador(administrador)
        resultado = conexion.execute(text("""
            INSERT INTO usuarios (nombre, email, telefono, password_hash, rol)
            VALUES (:nombre, :email, :telefono, :password_hash, 'personal')
        """), {"nombre": usuario["nombre"], "email": usuario["email"],
               "telefono": usuario["telefono"], "password_hash": password_hash})
        usuario_id = resultado.lastrowid
    return {"id": usuario_id, "nombre": usuario["nombre"], "email": usuario["email"],
            "telefono": usuario["telefono"], "rol": "personal", "activo": True}


def cambiar_estado_usuario(motor, administrador_id, usuario_id, datos):
    if not isinstance(datos, dict) or set(datos) != {"activo"} or type(datos["activo"]) is not bool:
        raise ValueError("Envía únicamente activo como booleano true o false.")
    if not 1 <= usuario_id <= 4294967295:
        raise ValueError("El identificador está fuera del rango permitido.")
    if usuario_id == administrador_id and not datos["activo"]:
        raise ConflictoUsuario("No puedes desactivar tu propia cuenta.")
    with motor.begin() as conexion:
        # Orden común con las reservas. Revalidar al actor bajo bloqueo impide
        # que dos administradores se desactiven mutuamente a la vez.
        filas = {}
        for identificador in sorted({administrador_id, usuario_id}):
            filas[identificador] = conexion.execute(text(
                "SELECT id, rol, activo FROM usuarios WHERE id = :id FOR UPDATE"
            ), {"id": identificador}).mappings().first()
        _validar_administrador(filas[administrador_id])
        usuario = filas[usuario_id]
        if usuario is None:
            return None
        cambio = bool(usuario["activo"]) != datos["activo"]
        conexion.execute(text("UPDATE usuarios SET activo = :activo WHERE id = :id"),
                         {"activo": int(datos["activo"]), "id": usuario_id})
        if cambio and not datos["activo"]:
            # La reactivación no debe volver a habilitar tokens anteriores.
            conexion.execute(text("""
                INSERT INTO sesiones_usuario(usuario_id,version) VALUES(:id,1)
                ON DUPLICATE KEY UPDATE version=version+1
            """), {"id": usuario_id})
    return {"id": usuario_id, "activo": datos["activo"], "cambio_realizado": cambio}
