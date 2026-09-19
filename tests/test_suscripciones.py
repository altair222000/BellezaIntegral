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
