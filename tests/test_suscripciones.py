from sqlalchemy import text

from test_flujos import call


def create_plan(client, headers):
    return call(
        client,
        headers,
        "/admin/planes-suscripcion",
        "POST",
        {
            "nombre": "Plan Test",
            "descripcion": "Suscripción mensual de prueba",
            "precio_mensual": "100.00",
            "duracion_meses": 1,
            "descuento_servicios": 10,
            "descuento_productos": 5,
            "acumulable_promociones": False,
        },
        id=1,
        expected=201,
    )["data"]["id"]


def test_client_can_subscribe_and_read(client, headers):
    plan_id = create_plan(client, headers)
    result = call(
        client,
        headers,
        "/suscripciones",
        "POST",
        {
            "plan_id": plan_id,
            "metodo_pago": "efectivo",
            "clave_operacion": "suscripcion_test_0001",
        },
        id=2,
        expected=201,
    )
    assert result["data"]["estado"] == "activa"
    assert result["data"]["pago_simulado"] is True

    mine = call(client, headers, "/suscripciones/mia", id=2)
    assert mine["data"]["id"] == result["data"]["id"]


def test_subscribe_is_idempotent(client, headers):
    plan_id = create_plan(client, headers)
    payload = {
        "plan_id": plan_id,
        "metodo_pago": "efectivo",
        "clave_operacion": "suscripcion_test_0002",
    }
    first = call(
        client, headers, "/suscripciones", "POST",
        payload, id=2, expected=201,
    )
    second = call(
        client, headers, "/suscripciones", "POST",
        payload, id=2, expected=200,
    )
    assert first["data"]["id"] == second["data"]["id"]
    assert second["data"]["cambio_realizado"] is False


def test_cannot_have_two_active_subscriptions(client, headers):
    plan_id = create_plan(client, headers)
    call(
        client,
        headers,
        "/suscripciones",
        "POST",
        {
            "plan_id": plan_id,
            "metodo_pago": "efectivo",
            "clave_operacion": "suscripcion_test_0003",
        },
        id=2,
        expected=201,
    )
    r = client.post(
        "/api/v1/suscripciones",
        headers=headers(2),
        json={
            "plan_id": plan_id,
            "metodo_pago": "efectivo",
            "clave_operacion": "suscripcion_test_0004",
        },
    )
    assert r.status_code == 409


def test_renew_extends_end_date(client, headers, motor):
    plan_id = create_plan(client, headers)
    sub = call(
        client,
        headers,
        "/suscripciones",
        "POST",
        {
            "plan_id": plan_id,
            "metodo_pago": "efectivo",
            "clave_operacion": "suscripcion_test_0005",
        },
        id=2,
        expected=201,
    )["data"]

    with motor.connect() as c:
        before = c.execute(
            text("SELECT fecha_fin FROM suscripciones WHERE id=:id"),
            {"id": sub["id"]},
        ).scalar_one()

    call(
        client,
        headers,
        f"/suscripciones/{sub['id']}/renovar",
        "POST",
        {
            "metodo_pago": "efectivo",
            "clave_operacion": "suscripcion_test_0006",
        },
        id=2,
        expected=201,
    )

    with motor.connect() as c:
        after = c.execute(
            text("SELECT fecha_fin FROM suscripciones WHERE id=:id"),
            {"id": sub["id"]},
        ).scalar_one()

    assert after > before


def test_cancel_subscription(client, headers):
    plan_id = create_plan(client, headers)
    sub = call(
        client,
        headers,
        "/suscripciones",
        "POST",
        {
            "plan_id": plan_id,
            "metodo_pago": "efectivo",
            "clave_operacion": "suscripcion_test_0007",
        },
        id=2,
        expected=201,
    )["data"]

    result = call(
        client,
        headers,
        f"/suscripciones/{sub['id']}/cancelar",
        "PATCH",
        {"motivo": "Prueba de cancelación"},
        id=2,
    )
    assert result["data"]["estado"] == "cancelada"


def test_health_subscriptions(client):
    r = client.get("/api/v1/health/suscripciones")
    assert r.status_code == 200
    data = r.get_json()["data"]
    assert data["tablas"] == 3
    assert data["vistas"] == 2
    assert data["triggers"] >= 9


def test_product_discount_is_shown_and_applied_to_order(
    client,
    headers,
):
    plan_id = create_plan(client, headers)

    subscription = call(
        client,
        headers,
        "/suscripciones",
        "POST",
        {
            "plan_id": plan_id,
            "metodo_pago": "efectivo",
            "clave_operacion": "suscripcion_descuento_0001",
        },
        id=2,
        expected=201,
    )["data"]

    product_id = call(
        client,
        headers,
        "/admin/productos",
        "POST",
        {
            "nombre": "Producto membresía",
            "categoria": "Belleza",
            "tipo": "venta",
            "precio": "20.00",
        },
        id=1,
        expected=201,
    )["data"]["id"]

    call(
        client,
        headers,
        "/admin/inventario/movimientos",
        "POST",
        {
            "producto_id": product_id,
            "tipo": "entrada",
            "cantidad": 5,
            "motivo": "Prueba descuento membresía",
        },
        id=1,
        expected=201,
    )

    catalog = call(
        client,
        headers,
        "/productos?pagina=1&limite=20",
        id=2,
    )
    product = next(
        p for p in catalog["data"]
        if p["id"] == product_id
    )

    assert product["precio_original"] == "20.00"
    assert product["precio"] == "19.00"
    assert product["descuento_suscripcion"] == 5

    order = call(
        client,
        headers,
        "/pedidos",
        "POST",
        {
            "items": [
                {
                    "producto_id": product_id,
                    "cantidad": 2,
                }
            ],
            "nombre_entrega": "Cliente membresía",
            "telefono_entrega": "55550101",
            "direccion_entrega": "Dirección prueba",
            "metodo_pago": "efectivo",
            "clave_operacion": "pedido_membresia_0001",
        },
        id=2,
        expected=201,
    )["data"]

    assert order["total"] == "38.00"
    assert order["descuento_suscripcion"] == 5
    assert order["detalle"][0]["precio_unitario"] == "19.00"
    assert subscription["descuento_productos_contratado"] == 5


def test_anonymous_product_catalog_keeps_base_price(
    client,
    headers,
):
    product_id = call(
        client,
        headers,
        "/admin/productos",
        "POST",
        {
            "nombre": "Producto público",
            "categoria": "Belleza",
            "tipo": "venta",
            "precio": "25.00",
        },
        id=1,
        expected=201,
    )["data"]["id"]

    r = client.get("/api/v1/productos?pagina=1&limite=20")
    assert r.status_code == 200
    product = next(
        p for p in r.get_json()["data"]
        if p["id"] == product_id
    )
    assert product["precio_original"] == "25.00"
    assert product["precio"] == "25.00"
    assert product["descuento_suscripcion"] == 0
