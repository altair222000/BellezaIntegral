"""Instala o verifica database/008_suscripciones.sql."""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sql_utils import cargar_sentencias

ARCHIVO = ROOT / "database" / "008_suscripciones.sql"


def motor_desde_env():
    load_dotenv(ROOT / ".env")
    requeridas = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    faltan = [k for k in requeridas if not os.getenv(k)]
    if faltan:
        raise RuntimeError("Faltan variables: " + ", ".join(faltan))

    opts = {
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "8")),
        "read_timeout": int(os.getenv("DB_READ_TIMEOUT", "30")),
        "write_timeout": int(os.getenv("DB_WRITE_TIMEOUT", "30")),
        "init_command": "SET time_zone='-06:00'",
    }
    if os.getenv("DB_SSL_CA"):
        opts.update(
            ssl_ca=os.environ["DB_SSL_CA"],
            ssl_verify_cert=True,
            ssl_verify_identity=True,
        )

    return create_engine(
        URL.create(
            "mysql+pymysql",
            username=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            host=os.environ["DB_HOST"],
            port=int(os.getenv("DB_PORT", "3306")),
            database=os.environ["DB_NAME"],
            query={"charset": "utf8mb4"},
        ),
        pool_pre_ping=True,
        connect_args=opts,
    )


def verificar_prerrequisitos(conexion):
    existentes = {
        r[0]
        for r in conexion.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema=DATABASE()
                  AND table_name IN (
                    'usuarios','auditoria_cambios','auditoria_eventos'
                  )
                """
            )
        )
    }
    requeridas = {"usuarios", "auditoria_cambios", "auditoria_eventos"}
    if existentes != requeridas:
        raise RuntimeError(
            "Faltan prerrequisitos: " + ", ".join(sorted(requeridas - existentes))
        )


def verificar(conexion):
    tables = {
        r[0]
        for r in conexion.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema=DATABASE()
                  AND table_name IN (
                    'planes_suscripcion','suscripciones','pagos_suscripcion'
                  )
                """
            )
        )
    }
    if tables != {"planes_suscripcion", "suscripciones", "pagos_suscripcion"}:
        raise RuntimeError("Faltan tablas del módulo de suscripciones.")

    views = {
        r[0]
        for r in conexion.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema=DATABASE()
                  AND table_name IN (
                    'vw_suscripciones_detalle','vw_suscripciones_activas'
                  )
                """
            )
        )
    }
    if views != {"vw_suscripciones_detalle", "vw_suscripciones_activas"}:
        raise RuntimeError("Faltan vistas del módulo de suscripciones.")

    triggers = conexion.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.triggers
            WHERE trigger_schema=DATABASE()
              AND trigger_name LIKE '%suscripcion%'
            """
        )
    ).scalar_one()
    if triggers < 9:
        raise RuntimeError(
            f"Se esperaban al menos 9 triggers y se encontraron {triggers}."
        )

    print(
        f"OK: suscripciones verificadas "
        f"({len(tables)} tablas, {len(views)} vistas, {triggers} triggers)."
    )


def aplicar(motor):
    if not ARCHIVO.exists():
        raise RuntimeError(f"No existe {ARCHIVO}")

    with motor.connect() as conexion:
        verificar_prerrequisitos(conexion)

    raw = motor.raw_connection()
    cursor = raw.cursor()
    try:
        cursor.execute("SELECT DATABASE()")
        base = cursor.fetchone()[0]
        print(f"Base destino: {base}")
        print(f"Aplicando {ARCHIVO.name} ...")

        for numero, sentencia in enumerate(cargar_sentencias(ARCHIVO), 1):
            inicio = sentencia.lstrip().upper()
            if inicio.startswith("CREATE DATABASE") or inicio.startswith("USE "):
                continue
            try:
                cursor.execute(sentencia)
                raw.commit()
            except Exception as exc:
                raw.rollback()
                fragmento = " ".join(sentencia.strip().split())[:220]
                raise RuntimeError(
                    f"Falló {ARCHIVO.name}, sentencia {numero}.\n"
                    f"Error real: {exc}\n"
                    f"Inicio: {fragmento}"
                ) from exc
        print("OK: script aplicado correctamente.")
    finally:
        try:
            cursor.close()
        finally:
            raw.close()


def main():
    parser = argparse.ArgumentParser(
        description="Instala o verifica suscripciones mensuales."
    )
    parser.add_argument("--solo-verificar", action="store_true")
    args = parser.parse_args()

    motor = motor_desde_env()
    try:
        if not args.solo_verificar:
            aplicar(motor)
        with motor.connect() as conexion:
            verificar(conexion)
    finally:
        motor.dispose()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, SQLAlchemyError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print("ERROR inesperado:", exc, file=sys.stderr)
        sys.exit(1)
