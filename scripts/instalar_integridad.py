"""Instala/actualiza auditoría, triggers, vistas y SP sobre DB_NAME.

No crea ni selecciona otra base de datos. Está pensado para hosting MySQL donde
el proveedor entrega una base ya creada y limita el permiso CREATE DATABASE.

La instalación usa un cursor DBAPI directo de PyMySQL para evitar que
SQLAlchemy/PyMySQL interpreten expresiones MySQL que contienen signos %, por
ejemplo DATE_FORMAT(fecha, '%Y%m%d') o LIKE '%texto%'.
"""

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


ARCHIVOS = [
    ROOT / "database" / "006_integridad_auditoria.sql",
    ROOT / "database" / "007_compatibilidad_api.sql",
]


def motor_desde_env():
    """Crea el Engine de SQLAlchemy usando las variables definidas en .env."""
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


def verificar(conexion):
    """Verifica que la capa de integridad haya quedado instalada."""
    tablas = {
        r[0]
        for r in conexion.execute(
            text("SHOW FULL TABLES WHERE Table_type='BASE TABLE'")
        )
    }

    requeridas = {
        "usuarios",
        "servicios",
        "disponibilidades",
        "citas",
        "productos",
        "pedidos",
        "pedido_detalle",
        "movimientos_inventario",
        "promociones",
        "puntos_historial",
        "auditoria_cambios",
        "auditoria_eventos",
    }

    faltan = requeridas - tablas
    if faltan:
        raise RuntimeError(
            "Faltan tablas requeridas: " + ", ".join(sorted(faltan))
        )

    vistas = {
        r[0]
        for r in conexion.execute(
            text("SHOW FULL TABLES WHERE Table_type='VIEW'")
        )
    }

    vistas_req = {
        "vw_citas_detalle",
        "vw_inventario_actual",
        "vw_resumen_pedidos",
        "vw_clientes_fidelizacion",
        "vw_promociones_vigentes",
    }

    if not vistas_req <= vistas:
        raise RuntimeError(
            "Faltan vistas: " + ", ".join(sorted(vistas_req - vistas))
        )

    rutinas = {
        r[0]
        for r in conexion.execute(
            text(
                """
                SELECT routine_name
                FROM information_schema.routines
                WHERE routine_schema = DATABASE()
                """
            )
        )
    }

    req_sp = {
        "sp_registrar_movimiento_inventario",
        "sp_ajustar_puntos",
        "sp_crear_cita",
        "sp_asignar_personal_cita",
        "sp_actualizar_estado_cita",
        "sp_confirmar_pedido",
        "sp_cancelar_pedido",
        "fn_total_pedido",
        "fn_stock_suficiente",
        "fn_saldo_puntos",
    }

    if not req_sp <= rutinas:
        raise RuntimeError(
            "Faltan rutinas: " + ", ".join(sorted(req_sp - rutinas))
        )

    triggers = conexion.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.triggers
            WHERE trigger_schema = DATABASE()
            """
        )
    ).scalar_one()

    if triggers < 40:
        raise RuntimeError(
            f"Se esperaban al menos 40 triggers y se encontraron {triggers}."
        )

    print(f"OK: esquema de integridad verificado ({triggers} triggers).")
    print(f"OK: {len(vistas_req)} vistas requeridas presentes.")
    print(f"OK: {len(req_sp)} rutinas requeridas presentes.")


def ejecutar_archivos_sql(motor):
    """Ejecuta los scripts SQL usando el cursor DBAPI directo."""
    raw = motor.raw_connection()
    cursor = raw.cursor()

    try:
        cursor.execute("SELECT DATABASE()")
        fila = cursor.fetchone()
        base = fila[0] if fila else None
        print(f"Base destino: {base}")

        if not base:
            raise RuntimeError("No hay una base de datos seleccionada.")

        for archivo in ARCHIVOS:
            if not archivo.exists():
                raise RuntimeError(f"No existe el archivo SQL: {archivo}")

            print(f"Aplicando {archivo.name} ...")

            sentencias = cargar_sentencias(archivo)

            for numero, sentencia in enumerate(sentencias, 1):
                inicio = sentencia.lstrip().upper()

                # El instalador trabaja únicamente sobre DB_NAME del .env.
                if inicio.startswith("CREATE DATABASE") or inicio.startswith("USE "):
                    continue

                try:
                    # Importante: no pasar un segundo argumento a execute().
                    # De esta forma PyMySQL no intenta interpolar los % que
                    # forman parte de DATE_FORMAT(), LIKE, etc.
                    cursor.execute(sentencia)
                    raw.commit()

                except Exception as exc:
                    raw.rollback()

                    fragmento = " ".join(sentencia.strip().split())[:220]

                    raise RuntimeError(
                        f"Falló {archivo.name}, sentencia {numero}.\n"
                        f"Error real de MySQL/PyMySQL: {exc}\n"
                        f"Inicio de la sentencia: {fragmento}"
                    ) from exc

            print(f"OK: {archivo.name} aplicado correctamente.")

    finally:
        try:
            cursor.close()
        finally:
            raw.close()


def main():
    parser = argparse.ArgumentParser(
        description="Instala o verifica la capa de integridad de Belleza Integral."
    )
    parser.add_argument(
        "--solo-verificar",
        action="store_true",
        help="No modifica la BD; únicamente comprueba objetos requeridos.",
    )
    args = parser.parse_args()

    motor = motor_desde_env()

    try:
        if not args.solo_verificar:
            ejecutar_archivos_sql(motor)
            print("Capa de integridad instalada.")

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
        print(f"ERROR inesperado: {exc}", file=sys.stderr)
        sys.exit(1)
