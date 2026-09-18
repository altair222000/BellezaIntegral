import os

from flask import g, has_request_context, request
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL


def _contexto_request():
    actor_id = None
    ip = None
    if has_request_context():
        usuario = getattr(g, "usuario_actual", None)
        if isinstance(usuario, dict):
            actor_id = usuario.get("id")
        ip = request.remote_addr
    return actor_id, ip


def crear_motor():
    campos = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
    faltantes = [campo for campo in campos if not os.getenv(campo)]

    if faltantes:
        raise RuntimeError("Falta configuración: " + ", ".join(faltantes))

    url = URL.create(
        drivername="mysql+pymysql",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.environ["DB_NAME"],
        query={"charset": "utf8mb4"},
    )

    opciones = {
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "8")),
        "read_timeout": int(os.getenv("DB_READ_TIMEOUT", "15")),
        "write_timeout": int(os.getenv("DB_WRITE_TIMEOUT", "15")),
        "init_command": "SET time_zone = '-06:00'",
    }
    if os.getenv("DB_SSL_CA"):
        opciones.update(
            ssl_ca=os.environ["DB_SSL_CA"],
            ssl_verify_cert=True,
            ssl_verify_identity=True,
        )

    motor = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        connect_args=opciones,
    )

    @event.listens_for(motor, "checkout")
    def _limpiar_variables_sesion(dbapi_connection, connection_record, connection_proxy):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(
                "SET @app_usuario_id=NULL, @app_ip=NULL, "
                "@app_correlacion_id=NULL, "
                "@permitir_cambio_stock=NULL, @permitir_cambio_puntos=NULL"
            )
        finally:
            cursor.close()

    @event.listens_for(motor, "begin")
    def _iniciar_contexto_auditoria(connection):
        actor_id, ip = _contexto_request()
        # exec_driver_sql evita depender del compilador SQL para variables MySQL.
        connection.exec_driver_sql(
            "SET @app_usuario_id=%s, @app_ip=%s, "
            "@app_correlacion_id=UUID(), "
            "@permitir_cambio_stock=NULL, @permitir_cambio_puntos=NULL",
            (actor_id, ip),
        )

    return motor
