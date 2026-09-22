import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


def test_health_base_y_esquema_completo(client):
    db = client.get("/api/v1/health/db")
    assert db.status_code == 200
    assert db.get_json()["data"]["database"] == "ok"

    schema = client.get("/api/v1/health/schema")
    assert schema.status_code == 200, schema.get_data(as_text=True)
    data = schema.get_json()["data"]
    assert data["tablas_auditoria"] == 2
    assert data["vistas"] == 5
    assert data["triggers"] >= 40
    assert data["rutinas"] == 10


def test_stock_no_puede_modificarse_fuera_del_flujo_controlado(motor):
    with motor.begin() as c:
        producto_id = c.execute(text(
            "INSERT INTO productos(nombre,categoria,tipo,precio,stock) "
            "VALUES('Producto protegido','CI','venta',10.00,5)"
        )).lastrowid

    with pytest.raises(DBAPIError):
        with motor.begin() as c:
            c.execute(
                text("UPDATE productos SET stock=99 WHERE id=:id"),
                {"id": producto_id},
            )

    with motor.connect() as c:
        assert c.execute(
            text("SELECT stock FROM productos WHERE id=:id"),
            {"id": producto_id},
        ).scalar_one() == 5


def test_puntos_no_pueden_modificarse_fuera_del_flujo_controlado(motor):
    with pytest.raises(DBAPIError):
        with motor.begin() as c:
            c.execute(text("UPDATE usuarios SET puntos=500 WHERE id=2"))

    with motor.connect() as c:
        assert c.execute(text("SELECT puntos FROM usuarios WHERE id=2")).scalar_one() == 0


def test_operaciones_generan_auditoria(client, headers, motor):
    respuesta = client.post(
        "/api/v1/servicios",
        headers=headers(),
        json={
            "nombre": "Servicio auditado",
            "descripcion": "Creado durante CI",
            "categoria": "Pruebas",
            "duracion_min": 45,
            "precio": "80.00",
        },
    )
    assert respuesta.status_code == 201, respuesta.get_data(as_text=True)

    with motor.connect() as c:
        cantidad = c.execute(text(
            "SELECT COUNT(*) FROM auditoria_cambios "
            "WHERE tabla='servicios' AND operacion='INSERT'"
        )).scalar_one()
    assert cantidad >= 1


def test_vistas_principales_consultables(motor):
    vistas = [
        "vw_citas_detalle",
        "vw_inventario_actual",
        "vw_resumen_pedidos",
        "vw_clientes_fidelizacion",
        "vw_promociones_vigentes",
    ]
    with motor.connect() as c:
        for vista in vistas:
            c.exec_driver_sql(f"SELECT * FROM {vista} LIMIT 1").all()
