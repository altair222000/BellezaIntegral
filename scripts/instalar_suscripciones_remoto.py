"""Ejecuta database/008_suscripciones.sql contra un MySQL remoto.

No guarda credenciales en Git. Los parámetros pueden venir de:
1. argumentos de línea de comandos;
2. variables REMOTE_DB_*;
3. archivo local .env.remote (ignorado por Git).

Ejemplos:
    python scripts/instalar_suscripciones_remoto.py --verify
    python scripts/instalar_suscripciones_remoto.py --apply
    python scripts/instalar_suscripciones_remoto.py \
        --host mysql.ejemplo.com --port 3306 \
        --database belleza_integral --user belleza_app --apply
"""
import argparse
import getpass
import os
import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sql_utils import cargar_sentencias

SQL_FILE = ROOT / "database" / "008_suscripciones.sql"
ENV_FILE = ROOT / ".env.remote"

REQUIRED_BASE_TABLES = {
    "usuarios",
    "auditoria_cambios",
    "auditoria_eventos",
}
MODULE_TABLES = {
    "planes_suscripcion",
    "suscripciones",
    "pagos_suscripcion",
}
MODULE_VIEWS = {
    "vw_suscripciones_detalle",
    "vw_suscripciones_activas",
}


def arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Instala o verifica el módulo de suscripciones "
            "en un servidor MySQL remoto."
        )
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Aplica database/008_suscripciones.sql.",
    )
    mode.add_argument(
        "--verify",
        action="store_true",
        help="Solo verifica; no modifica la base.",
    )

    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--database")
    parser.add_argument("--user")
    parser.add_argument(
        "--password",
        help=(
            "No recomendado: queda en el historial del shell. "
            "Si se omite se solicita de forma segura."
        ),
    )
    parser.add_argument(
        "--ssl-ca",
        help="Ruta local al certificado CA si el proveedor exige SSL.",
    )
    return parser.parse_args()


def config(args):
    load_dotenv(ENV_FILE, override=False)

    values = {
        "host": args.host or os.getenv("REMOTE_DB_HOST"),
        "port": args.port or int(os.getenv("REMOTE_DB_PORT", "3306")),
        "database": args.database or os.getenv("REMOTE_DB_NAME"),
        "user": args.user or os.getenv("REMOTE_DB_USER"),
        "password": args.password or os.getenv("REMOTE_DB_PASSWORD"),
        "ssl_ca": args.ssl_ca or os.getenv("REMOTE_DB_SSL_CA"),
    }

    missing = [
        name
        for name in ("host", "database", "user")
        if not values[name]
    ]
    if missing:
        raise RuntimeError(
            "Faltan parámetros: "
            + ", ".join(missing)
            + ". Usa argumentos, REMOTE_DB_* o .env.remote."
        )

    if not values["password"]:
        values["password"] = getpass.getpass(
            f"Contraseña MySQL para {values['user']}@{values['host']}: "
        )

    return values


def connect(cfg):
    kwargs = {
        "host": cfg["host"],
        "port": cfg["port"],
        "user": cfg["user"],
        "password": cfg["password"],
        "database": cfg["database"],
        "charset": "utf8mb4",
        "autocommit": False,
        "connect_timeout": 10,
        "read_timeout": 30,
        "write_timeout": 30,
        "cursorclass": pymysql.cursors.Cursor,
    }

    if cfg["ssl_ca"]:
        kwargs.update(
            ssl_ca=cfg["ssl_ca"],
            ssl_verify_cert=True,
            ssl_verify_identity=True,
        )

    connection = pymysql.connect(**kwargs)
    with connection.cursor() as cursor:
        cursor.execute("SET time_zone='-06:00'")
    return connection


def names(connection, query, params=()):
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return {row[0] for row in cursor.fetchall()}


def server_info(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT VERSION(), DATABASE(), CURRENT_USER()"
        )
        version, database, current_user = cursor.fetchone()
    return version, database, current_user


def verify_prerequisites(connection):
    found = names(
        connection,
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema=DATABASE()
          AND table_type='BASE TABLE'
          AND table_name IN (
              'usuarios',
              'auditoria_cambios',
              'auditoria_eventos'
          )
        """,
    )

    missing = REQUIRED_BASE_TABLES - found
    if missing:
        raise RuntimeError(
            "La base remota no tiene los prerrequisitos: "
            + ", ".join(sorted(missing))
            + ". Instala primero la capa base/integridad."
        )


def verify_module(connection):
    tables = names(
        connection,
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema=DATABASE()
          AND table_type='BASE TABLE'
          AND table_name IN (
              'planes_suscripcion',
              'suscripciones',
              'pagos_suscripcion'
          )
        """,
    )

    views = names(
        connection,
        """
        SELECT table_name
        FROM information_schema.views
        WHERE table_schema=DATABASE()
          AND table_name IN (
              'vw_suscripciones_detalle',
              'vw_suscripciones_activas'
          )
        """,
    )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.triggers
            WHERE trigger_schema=DATABASE()
              AND trigger_name LIKE '%suscripcion%'
            """
        )
        trigger_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM planes_suscripcion
            WHERE nombre='Membresía Mensual'
            """
        )
        initial_plan = cursor.fetchone()[0]

    missing_tables = MODULE_TABLES - tables
    missing_views = MODULE_VIEWS - views

    if missing_tables or missing_views or trigger_count < 9:
        details = []
        if missing_tables:
            details.append(
                "tablas: " + ", ".join(sorted(missing_tables))
            )
        if missing_views:
            details.append(
                "vistas: " + ", ".join(sorted(missing_views))
            )
        if trigger_count < 9:
            details.append(
                f"triggers encontrados: {trigger_count} (mínimo 9)"
            )
        raise RuntimeError(
            "Módulo incompleto; " + "; ".join(details)
        )

    print("OK: 3 tablas de suscripciones.")
    print("OK: 2 vistas de suscripciones.")
    print(f"OK: {trigger_count} triggers de suscripciones.")
    print(
        "OK: plan inicial presente."
        if initial_plan
        else "ADVERTENCIA: no existe el plan inicial."
    )


def apply_sql(connection):
    if not SQL_FILE.exists():
        raise RuntimeError(
            f"No existe el script versionado: {SQL_FILE}"
        )

    statements = cargar_sentencias(SQL_FILE)
    print(f"Aplicando {SQL_FILE.name}: {len(statements)} sentencias.")

    for number, statement in enumerate(statements, 1):
        start = statement.lstrip().upper()

        if start.startswith("CREATE DATABASE") or start.startswith("USE "):
            continue

        try:
            with connection.cursor() as cursor:
                cursor.execute(statement)
            connection.commit()
        except Exception as exc:
            connection.rollback()
            fragment = " ".join(statement.split())[:220]
            raise RuntimeError(
                f"Falló la sentencia {number} de {SQL_FILE.name}.\n"
                f"MySQL: {exc}\n"
                f"Inicio: {fragment}"
            ) from exc


def main():
    args = arguments()
    cfg = config(args)

    print("Destino remoto:")
    print(f"  host:     {cfg['host']}:{cfg['port']}")
    print(f"  database: {cfg['database']}")
    print(f"  user:     {cfg['user']}")
    print(
        "  SSL CA:   "
        + (cfg["ssl_ca"] if cfg["ssl_ca"] else "no configurado")
    )

    connection = connect(cfg)
    try:
        version, database, current_user = server_info(connection)
        print(f"MySQL: {version}")
        print(f"Base confirmada por servidor: {database}")
        print(f"Usuario efectivo: {current_user}")

        if database != cfg["database"]:
            raise RuntimeError(
                "La base seleccionada no coincide con --database."
            )

        verify_prerequisites(connection)

        if args.apply:
            apply_sql(connection)
            print("OK: migración remota aplicada.")

        verify_module(connection)
        print("OK: verificación remota completada.")
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperación cancelada.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)
