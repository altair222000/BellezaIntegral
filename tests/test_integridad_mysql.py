import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError


TABLAS_REQUERIDAS = {
    "usuarios",
    "servicios",
    "disponibilidades",
    "citas",
    "productos",
    "pedidos",
    "pedido_detalle",
    "promociones",
    "puntos_historial",
    "movimientos_inventario",
    "tokens_revocados",
    "sesiones_usuario",
}


def test_base_mysql_y_esquema_disponibles(client, motor):
    respuesta = client.get("/api/v1/health/db")
    assert respuesta.status_code == 200
    assert respuesta.get_json()["data"]["database"] == "ok"

    with motor.connect() as conexion:
        tablas = {fila[0] for fila in conexion.execute(text("SHOW TABLES")).all()}

    assert TABLAS_REQUERIDAS <= tablas


def test_datos_semilla_son_coherentes(app, motor):
    with motor.connect() as conexion:
        filas = conexion.execute(
            text("SELECT id,email,rol,activo FROM usuarios ORDER BY id")
        ).mappings().all()

    assert len(filas) == 6
    assert [fila["rol"] for fila in filas] == [
        "administrador",
        "cliente",
        "personal",
        "cliente",
        "personal",
        "administrador",
    ]
    assert all(fila["activo"] == 1 for fila in filas)
    assert all(fila["email"].endswith("@example.com") for fila in filas)


def test_integridad_referencial_impide_cita_invalida(app, motor):
    with pytest.raises(IntegrityError):
        with motor.begin() as conexion:
            conexion.execute(
                text(
                    """
                    INSERT INTO citas(
                        cliente_id,personal_id,servicio_id,
                        fecha,hora,duracion_min,estado
                    )
                    VALUES(2,3,999999,CURRENT_DATE + INTERVAL 7 DAY,'10:00',60,'pendiente')
                    """
                )
            )


def test_restricciones_impiden_stock_negativo(app, motor):
    with motor.begin() as conexion:
        producto_id = conexion.execute(
            text(
                """
                INSERT INTO productos(nombre,categoria,tipo,precio,stock)
                VALUES('Producto CI','Pruebas','venta',10.00,1)
                """
            )
        ).lastrowid

    with pytest.raises(DBAPIError):
        with motor.begin() as conexion:
            conexion.execute(
                text("UPDATE productos SET stock = -1 WHERE id=:id"),
                {"id": producto_id},
            )

    with motor.connect() as conexion:
        stock = conexion.execute(
            text("SELECT stock FROM productos WHERE id=:id"),
            {"id": producto_id},
        ).scalar_one()

    assert stock == 1


def test_email_unico_protege_clientes(app, motor):
    with pytest.raises(IntegrityError):
        with motor.begin() as conexion:
            conexion.execute(
                text(
                    """
                    INSERT INTO usuarios(nombre,email,password_hash,rol)
                    VALUES('Duplicado','cuenta2@example.com','hash-prueba','cliente')
                    """
                )
            )
