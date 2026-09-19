"""Pruebas destructivas SOLO sobre una BD aislada cuyo nombre termine en _test."""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def motor():
    url = os.getenv("BELLEZA_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Configura BELLEZA_TEST_DATABASE_URL para ejecutar integración MySQL.")
    parsed = make_url(url)
    if not parsed.database or not parsed.database.endswith("_test"):
        pytest.fail("Se requiere una base aislada terminada en _test; se limpiarán sus datos.")

    e = create_engine(
        url,
        pool_size=25,
        max_overflow=10,
        connect_args={"init_command": "SET time_zone='-06:00'"},
    )

    @event.listens_for(e, "checkout")
    def reset_flags(dbapi_connection, connection_record, connection_proxy):
        cur = dbapi_connection.cursor()
        cur.execute(
            "SET @permitir_cambio_stock=NULL,@permitir_cambio_puntos=NULL,"
            "@app_usuario_id=NULL,@app_ip=NULL,@app_correlacion_id=NULL"
        )
        cur.close()

    with e.connect() as c:
        marker = c.execute(text("SHOW TABLES LIKE 'belleza_test_marker'")).first()
        tables = c.execute(text("SHOW TABLES")).all()
        if tables and not marker:
            pytest.fail("La base contiene tablas sin marcador de pruebas. Usa una base vacía.")
        c.execute(text("CREATE TABLE IF NOT EXISTS belleza_test_marker (id INT PRIMARY KEY)"))
        c.commit()

        from scripts.sql_utils import cargar_sentencias

        archivos = sorted((ROOT / "database").glob("00[1-8]_*.sql"))
        for f in archivos:
            for stmt in cargar_sentencias(f):
                limpio = stmt.lstrip()
                while limpio.startswith("--"):
                    partes = limpio.split("\n", 1)
                    limpio = partes[1].lstrip() if len(partes) > 1 else ""
                if not limpio or limpio.upper().startswith("USE "):
                    continue
                if f.name[:3] in {"001", "002", "003", "004"} and limpio.upper().startswith("CREATE TABLE "):
                    limpio = "CREATE TABLE IF NOT EXISTS " + limpio[len("CREATE TABLE "):]
                c.exec_driver_sql(limpio)
                c.commit()

    yield e
    e.dispose()


@pytest.fixture
def app(motor):
    with motor.connect() as c:
        c.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        for table in (
            "auditoria_eventos", "auditoria_cambios", "pagos_suscripcion",
            "suscripciones", "planes_suscripcion", "puntos_historial",
            "movimientos_inventario", "pedido_detalle", "pedidos", "promociones",
            "productos", "sesiones_usuario", "tokens_revocados", "citas",
            "disponibilidades", "servicios", "usuarios",
        ):
            c.exec_driver_sql("TRUNCATE TABLE " + table)
        c.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")
        c.commit()

    os.environ["JWT_SECRET_KEY"] = "CLAVE_SOLO_PRUEBAS_" * 6
    os.environ["CORS_ORIGINS"] = "http://localhost:5173"
    import app as module
    with patch("app.crear_motor", return_value=motor):
        a = module.create_app()
    a.config["TESTING"] = True

    from werkzeug.security import generate_password_hash
    hashed = generate_password_hash("PasswordTest2026!", method="scrypt")
    with motor.begin() as c:
        for id, rol in [
            (1, "administrador"), (2, "cliente"), (3, "personal"),
            (4, "cliente"), (5, "personal"), (6, "administrador"),
        ]:
            c.execute(
                text("INSERT INTO usuarios(id,nombre,email,password_hash,rol) VALUES(:id,:nombre,:email,:hash,:rol)"),
                {"id": id, "nombre": "Cuenta " + str(id), "email": f"cuenta{id}@example.com", "hash": hashed, "rol": rol},
            )
    return a


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def headers(app):
    from flask_jwt_extended import create_access_token

    def make(id=1):
        with app.app_context():
            return {
                "Authorization": "Bearer " + create_access_token(
                    identity=str(id), additional_claims={"version": 0}
                )
            }

    return make
