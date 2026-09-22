"""Prepara una base MySQL aislada para CI y carga datos de referencia coherentes."""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.sql_utils import cargar_sentencias

TABLAS_LIMPIAR = (
    "auditoria_eventos", "auditoria_cambios", "puntos_historial",
    "movimientos_inventario", "pedido_detalle", "pedidos", "promociones",
    "productos", "sesiones_usuario", "tokens_revocados", "citas",
    "disponibilidades", "servicios", "usuarios",
)


def ejecutar_sql(motor):
    archivos = sorted((ROOT / "tests" / "sql").glob("*.sql"))
    if not archivos:
        raise RuntimeError("No se encontraron scripts SQL de CI en tests/sql.")

    with motor.connect() as conexion:
        conexion.execute(text(
            "CREATE TABLE IF NOT EXISTS belleza_test_marker "
            "(id INT PRIMARY KEY, creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        ))
        conexion.commit()

        for archivo in archivos:
            print(f"Aplicando {archivo.name} ...")
            for sentencia in cargar_sentencias(archivo):
                limpio = sentencia.lstrip()
                if not limpio:
                    continue
                mayus = limpio.upper()
                if mayus.startswith("CREATE DATABASE") or mayus.startswith("USE "):
                    continue
                conexion.exec_driver_sql(sentencia)
                conexion.commit()


def limpiar(motor):
    with motor.connect() as conexion:
        conexion.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        for tabla in TABLAS_LIMPIAR:
            conexion.exec_driver_sql(f"TRUNCATE TABLE {tabla}")
        conexion.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")
        conexion.commit()


def sembrar(motor):
    password_hash = generate_password_hash("PasswordTest2026!", method="scrypt")
    fecha_cita = date.today() + timedelta(days=7)

    with motor.begin() as conexion:
        usuarios = [
            (1, "Administración CI", "admin.ci@example.com", "administrador"),
            (2, "Cliente CI", "cliente.ci@example.com", "cliente"),
            (3, "Profesional CI", "personal.ci@example.com", "personal"),
        ]
        for identificador, nombre, email, rol in usuarios:
            conexion.execute(text(
                "INSERT INTO usuarios(id,nombre,email,password_hash,rol) "
                "VALUES(:id,:nombre,:email,:hash,:rol)"
            ), {"id": identificador, "nombre": nombre, "email": email,
                "hash": password_hash, "rol": rol})

        servicio_id = conexion.execute(text(
            "INSERT INTO servicios(nombre,descripcion,categoria,duracion_min,precio) "
            "VALUES('Manicura CI','Servicio de referencia para CI','Uñas',60,125.00)"
        )).lastrowid

        conexion.execute(text(
            "INSERT INTO disponibilidades(personal_id,dia_semana,hora_inicio,hora_fin) "
            "VALUES(3,:dia,'09:00','17:00')"
        ), {"dia": fecha_cita.isoweekday()})

        conexion.execute(text(
            "INSERT INTO citas(cliente_id,personal_id,servicio_id,fecha,hora,duracion_min,estado) "
            "VALUES(2,3,:servicio,:fecha,'10:00',60,'pendiente')"
        ), {"servicio": servicio_id, "fecha": fecha_cita})

        conexion.execute(text(
            "INSERT INTO productos(nombre,descripcion,categoria,tipo,precio,stock) "
            "VALUES('Esmalte CI','Producto de referencia para CI','Belleza','venta',25.00,10)"
        ))

        conexion.execute(text(
            "INSERT INTO promociones(titulo,descripcion,descuento_porcentaje,fecha_inicio,fecha_fin,puntos_costo) "
            "VALUES('Promoción CI','Beneficio de referencia',10,CURRENT_DATE,"
            "DATE_ADD(CURRENT_DATE,INTERVAL 30 DAY),50)"
        ))


def verificar(motor):
    requeridas = {
        "usuarios", "servicios", "disponibilidades", "citas", "productos",
        "pedidos", "pedido_detalle", "promociones", "puntos_historial",
        "movimientos_inventario", "tokens_revocados", "sesiones_usuario",
        "auditoria_cambios", "auditoria_eventos",
    }
    with motor.connect() as conexion:
        tablas = {r[0] for r in conexion.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_type='BASE TABLE'"
        ))}
        faltan = requeridas - tablas
        if faltan:
            raise RuntimeError("Faltan tablas CI: " + ", ".join(sorted(faltan)))

        vistas = conexion.execute(text(
            "SELECT COUNT(*) FROM information_schema.views WHERE table_schema=DATABASE()"
        )).scalar_one()
        triggers = conexion.execute(text(
            "SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema=DATABASE()"
        )).scalar_one()
        rutinas = conexion.execute(text(
            "SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema=DATABASE()"
        )).scalar_one()
        usuarios = conexion.execute(text("SELECT COUNT(*) FROM usuarios")).scalar_one()
        citas = conexion.execute(text("SELECT COUNT(*) FROM citas")).scalar_one()

    if vistas < 5 or triggers < 40 or rutinas < 10:
        raise RuntimeError(
            f"Capa de integridad incompleta: vistas={vistas}, triggers={triggers}, rutinas={rutinas}"
        )
    if usuarios < 3 or citas < 1:
        raise RuntimeError("La semilla de CI no fue cargada correctamente.")

    print(
        f"OK CI: {len(requeridas)} tablas requeridas, {vistas} vistas, "
        f"{triggers} triggers, {rutinas} rutinas, {usuarios} usuarios y {citas} cita."
    )


def main():
    url = os.getenv("BELLEZA_TEST_DATABASE_URL")
    if not url:
        raise RuntimeError("Falta BELLEZA_TEST_DATABASE_URL.")

    parsed = make_url(url)
    if not parsed.database or not parsed.database.endswith("_test"):
        raise RuntimeError("La base de CI debe terminar en _test.")

    motor = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"init_command": "SET time_zone='-06:00'"},
    )
    try:
        ejecutar_sql(motor)
        limpiar(motor)
        sembrar(motor)
        verificar(motor)
    finally:
        motor.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR CI: {exc}", file=sys.stderr)
        raise
