"""Planes y suscripciones mensuales de Belleza Integral."""
import hashlib
import json
import re
import uuid

from flask import Blueprint, g, request
from sqlalchemy import text

from .api_common import (
    ApiError, actor, body, boolean, endpoint, engine,
    integer, key, money, page, query, response, string,
)
from .permisos import requiere_roles


suscripciones = Blueprint("suscripciones", __name__, url_prefix="/api/v1")

PLAN_FIELDS = {
    "nombre", "descripcion", "precio_mensual", "duracion_meses",
    "descuento_servicios", "descuento_productos",
    "acumulable_promociones",
}


def plan_data(data):
    return {
        "nombre": string(data.get("nombre"), "nombre", 100),
        "descripcion": string(data.get("descripcion"), "descripcion", 255, True),
        "precio_mensual": money(data.get("precio_mensual")),
        "duracion_meses": integer(data.get("duracion_meses", 1), "duracion_meses", 1, 24),
        "descuento_servicios": integer(data.get("descuento_servicios", 0), "descuento_servicios", 0, 100),
        "descuento_productos": integer(data.get("descuento_productos", 0), "descuento_productos", 0, 100),
        "acumulable_promociones": boolean(
            data.get("acumulable_promociones", False),
            "acumulable_promociones",
        ),
    }


def payment_data(data):
    method = data.get("metodo_pago")
    if method not in ("efectivo", "tarjeta_simulada"):
        raise ApiError("Método permitido: efectivo o tarjeta_simulada.")

    last = data.get("tarjeta_ultimos4")
    if method == "tarjeta_simulada":
        if not isinstance(last, str) or not re.fullmatch(r"[0-9]{4}", last):
            raise ApiError("Envía únicamente cuatro dígitos ficticios.")
    elif last is not None:
        raise ApiError("Efectivo no requiere datos de tarjeta.")
    return method, last


def fingerprint(data):
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def subscription_json(c, subscription_id, owner=None):
    params = {"id": subscription_id}
    owner_sql = ""
    if owner is not None:
        params["owner"] = owner
        owner_sql = " AND usuario_id=:owner"

    row = c.execute(
        text(
            """
            SELECT *
            FROM vw_suscripciones_detalle
            WHERE suscripcion_id=:id
            """
            + owner_sql
        ),
        params,
    ).mappings().first()

    if not row:
        raise ApiError("Suscripción no encontrada.", 404)

    result = dict(row)
    result["id"] = result.pop("suscripcion_id")
    result["acumulable_promociones_contratado"] = bool(
        result["acumulable_promociones_contratado"]
    )
    return result


def payment_json(c, payment_id, owner=None):
    params = {"id": payment_id}
    owner_sql = ""
    if owner is not None:
        params["owner"] = owner
        owner_sql = " AND usuario_id=:owner"

    row = c.execute(
        text(
            """
            SELECT id,suscripcion_id,usuario_id,periodo_inicio,periodo_fin,
                   monto,metodo_pago,estado,tarjeta_ultimos4,
                   referencia_pago,fecha_pago,fecha_creacion
            FROM pagos_suscripcion
            WHERE id=:id
            """
            + owner_sql
        ),
        params,
    ).mappings().first()

    if not row:
        raise ApiError("Pago no encontrado.", 404)
    return dict(row)


@suscripciones.get("/planes-suscripcion")
@endpoint
def public_plans():
    query()
    with engine().connect() as c:
        return page(
            c,
            """
            SELECT id,nombre,descripcion,precio_mensual,duracion_meses,
                   descuento_servicios,descuento_productos,
                   acumulable_promociones
            FROM planes_suscripcion
            WHERE activo=1
            ORDER BY precio_mensual,id
            """,
        )


@suscripciones.get("/admin/planes-suscripcion")
@requiere_roles("administrador")
@endpoint
def admin_plans():
    with engine().connect() as c:
        return page(c, "SELECT * FROM planes_suscripcion ORDER BY id DESC")


@suscripciones.post("/admin/planes-suscripcion")
@requiere_roles("administrador")
@endpoint
def create_plan():
    data = plan_data(body(PLAN_FIELDS, {"nombre", "precio_mensual"}))
    with engine().begin() as c:
        actor(c, {"administrador"})
        plan_id = c.execute(
            text(
                """
                INSERT INTO planes_suscripcion(
                    nombre,descripcion,precio_mensual,duracion_meses,
                    descuento_servicios,descuento_productos,
                    acumulable_promociones
                )
                VALUES(
                    :nombre,:descripcion,:precio_mensual,:duracion_meses,
                    :descuento_servicios,:descuento_productos,
                    :acumulable_promociones
                )
                """
            ),
            data,
        ).lastrowid
    return response({"id": plan_id, **data, "activo": True}, status=201)


@suscripciones.put("/admin/planes-suscripcion/<int:plan_id>")
@requiere_roles("administrador")
@endpoint
def update_plan(plan_id):
    data = plan_data(body(PLAN_FIELDS, {"nombre", "precio_mensual"}))
    with engine().begin() as c:
        actor(c, {"administrador"})
        if not c.execute(
            text("SELECT id FROM planes_suscripcion WHERE id=:id FOR UPDATE"),
            {"id": plan_id},
        ).first():
            raise ApiError("Plan no encontrado.", 404)

        c.execute(
            text(
                """
                UPDATE planes_suscripcion
                SET nombre=:nombre,
                    descripcion=:descripcion,
                    precio_mensual=:precio_mensual,
                    duracion_meses=:duracion_meses,
                    descuento_servicios=:descuento_servicios,
                    descuento_productos=:descuento_productos,
                    acumulable_promociones=:acumulable_promociones
                WHERE id=:id
                """
            ),
            {**data, "id": plan_id},
        )
    return response({"id": plan_id, **data})


@suscripciones.patch("/admin/planes-suscripcion/<int:plan_id>/estado")
@requiere_roles("administrador")
@endpoint
def plan_status(plan_id):
    active = boolean(body({"activo"}, {"activo"})["activo"])
    with engine().begin() as c:
        actor(c, {"administrador"})
        if not c.execute(
            text("SELECT id FROM planes_suscripcion WHERE id=:id FOR UPDATE"),
            {"id": plan_id},
        ).first():
            raise ApiError("Plan no encontrado.", 404)
        c.execute(
            text("UPDATE planes_suscripcion SET activo=:activo WHERE id=:id"),
            {"id": plan_id, "activo": active},
        )
    return response({"id": plan_id, "activo": active})


@suscripciones.get("/suscripciones/mia")
@requiere_roles("cliente")
@endpoint
def mine():
    user_id = g.usuario_actual["id"]
    with engine().connect() as c:
        row = c.execute(
            text(
                """
                SELECT suscripcion_id
                FROM vw_suscripciones_detalle
                WHERE usuario_id=:usuario_id
                ORDER BY
                    (estado_efectivo='activa' AND fecha_fin>NOW()) DESC,
                    suscripcion_id DESC
                LIMIT 1
                """
            ),
            {"usuario_id": user_id},
        ).first()
        if not row:
            return response(None, message="No tienes suscripciones.")
        return response(subscription_json(c, row[0], user_id))


@suscripciones.get("/suscripciones/mis-pagos")
@requiere_roles("cliente")
@endpoint
def my_payments():
    with engine().connect() as c:
        return page(
            c,
            """
            SELECT id,suscripcion_id,periodo_inicio,periodo_fin,monto,
                   metodo_pago,estado,tarjeta_ultimos4,
                   referencia_pago,fecha_pago,fecha_creacion
            FROM pagos_suscripcion
            WHERE usuario_id=:usuario_id
            ORDER BY id DESC
            """,
            {"usuario_id": g.usuario_actual["id"]},
        )


@suscripciones.get("/suscripciones/beneficios")
@requiere_roles("cliente")
@endpoint
def benefits():
    user_id = g.usuario_actual["id"]
    with engine().connect() as c:
        row = c.execute(
            text(
                """
                SELECT suscripcion_id,plan,fecha_fin,
                       descuento_servicios_contratado,
                       descuento_productos_contratado,
                       acumulable_promociones_contratado
                FROM vw_suscripciones_activas
                WHERE usuario_id=:usuario_id
                ORDER BY fecha_fin DESC
                LIMIT 1
                """
            ),
            {"usuario_id": user_id},
        ).mappings().first()

        if not row:
            return response({
                "suscripcion_activa": False,
                "descuento_servicios": 0,
                "descuento_productos": 0,
                "acumulable_promociones": False,
            })

        return response({
            "suscripcion_activa": True,
            "suscripcion_id": row["suscripcion_id"],
            "plan": row["plan"],
            "fecha_fin": row["fecha_fin"],
            "descuento_servicios": row["descuento_servicios_contratado"],
            "descuento_productos": row["descuento_productos_contratado"],
            "acumulable_promociones": bool(
                row["acumulable_promociones_contratado"]
            ),
        })


@suscripciones.post("/suscripciones")
@requiere_roles("cliente")
@endpoint
def subscribe():
    data = body(
        {"plan_id", "metodo_pago", "tarjeta_ultimos4", "clave_operacion"},
        {"plan_id", "metodo_pago", "clave_operacion"},
    )
    plan_id = integer(data["plan_id"], "plan_id")
    key(data["clave_operacion"])
    method, last = payment_data(data)
    user_id = g.usuario_actual["id"]

    signed = {
        "plan_id": plan_id,
        "metodo_pago": method,
        "tarjeta_ultimos4": last,
        "clave_operacion": data["clave_operacion"],
    }
    digest = fingerprint(signed)

    with engine().begin() as c:
        actor(c, {"cliente"})

        old = c.execute(
            text(
                """
                SELECT id,solicitud_hash
                FROM suscripciones
                WHERE usuario_id=:usuario_id
                  AND clave_operacion=:clave
                """
            ),
            {"usuario_id": user_id, "clave": data["clave_operacion"]},
        ).mappings().first()

        if old:
            if old["solicitud_hash"] != digest:
                raise ApiError(
                    "La clave_operacion ya se usó para otro contenido.", 409
                )
            pay = c.execute(
                text(
                    """
                    SELECT id
                    FROM pagos_suscripcion
                    WHERE usuario_id=:usuario_id
                      AND clave_operacion=:clave
                    """
                ),
                {"usuario_id": user_id, "clave": data["clave_operacion"]},
            ).first()
            result = subscription_json(c, old["id"], user_id)
            if pay:
                result["pago"] = payment_json(c, pay[0], user_id)
            result["pago_simulado"] = True
            result["cambio_realizado"] = False
            return response(result, message="Suscripción ya registrada.")

        active = c.execute(
            text(
                """
                SELECT id
                FROM suscripciones
                WHERE usuario_id=:usuario_id
                  AND estado='activa'
                  AND fecha_fin>NOW()
                LIMIT 1
                FOR UPDATE
                """
            ),
            {"usuario_id": user_id},
        ).first()
        if active:
            raise ApiError("Ya tienes una suscripción activa.", 409)

        plan = c.execute(
            text(
                """
                SELECT *
                FROM planes_suscripcion
                WHERE id=:id AND activo=1
                FOR SHARE
                """
            ),
            {"id": plan_id},
        ).mappings().first()
        if not plan:
            raise ApiError("Plan no disponible.", 404)

        period = c.execute(
            text(
                """
                SELECT NOW() AS inicio,
                       DATE_ADD(NOW(), INTERVAL :meses MONTH) AS fin
                """
            ),
            {"meses": plan["duracion_meses"]},
        ).mappings().one()

        subscription_id = c.execute(
            text(
                """
                INSERT INTO suscripciones(
                    usuario_id,plan_id,fecha_inicio,fecha_fin,estado,
                    precio_mensual_contratado,duracion_meses_contratada,
                    descuento_servicios_contratado,
                    descuento_productos_contratado,
                    acumulable_promociones_contratado,
                    clave_operacion,solicitud_hash
                )
                VALUES(
                    :usuario_id,:plan_id,:inicio,:fin,'activa',
                    :precio,:duracion,:desc_serv,:desc_prod,:acum,
                    :clave,:hash
                )
                """
            ),
            {
                "usuario_id": user_id,
                "plan_id": plan["id"],
                "inicio": period["inicio"],
                "fin": period["fin"],
                "precio": plan["precio_mensual"],
                "duracion": plan["duracion_meses"],
                "desc_serv": plan["descuento_servicios"],
                "desc_prod": plan["descuento_productos"],
                "acum": plan["acumulable_promociones"],
                "clave": data["clave_operacion"],
                "hash": digest,
            },
        ).lastrowid

        reference = "DEMO-" + uuid.uuid4().hex[:20].upper()
        payment_id = c.execute(
            text(
                """
                INSERT INTO pagos_suscripcion(
                    suscripcion_id,usuario_id,periodo_inicio,periodo_fin,
                    monto,metodo_pago,estado,tarjeta_ultimos4,
                    referencia_pago,clave_operacion,solicitud_hash,fecha_pago
                )
                VALUES(
                    :suscripcion_id,:usuario_id,:inicio,:fin,
                    :monto,:metodo,'aprobado',:ultimos4,
                    :referencia,:clave,:hash,NOW()
                )
                """
            ),
            {
                "suscripcion_id": subscription_id,
                "usuario_id": user_id,
                "inicio": period["inicio"],
                "fin": period["fin"],
                "monto": plan["precio_mensual"],
                "metodo": method,
                "ultimos4": last,
                "referencia": reference,
                "clave": data["clave_operacion"],
                "hash": digest,
            },
        ).lastrowid

        result = subscription_json(c, subscription_id, user_id)
        result["pago"] = payment_json(c, payment_id, user_id)
        result["pago_simulado"] = True
        result["cambio_realizado"] = True

    return response(
        result,
        message="Suscripción activada. No se realizó ningún cobro real.",
        status=201,
    )


@suscripciones.post("/suscripciones/<int:subscription_id>/renovar")
@requiere_roles("cliente")
@endpoint
def renew(subscription_id):
    data = body(
        {"metodo_pago", "tarjeta_ultimos4", "clave_operacion"},
        {"metodo_pago", "clave_operacion"},
    )
    key(data["clave_operacion"])
    method, last = payment_data(data)
    user_id = g.usuario_actual["id"]

    signed = {
        "suscripcion_id": subscription_id,
        "metodo_pago": method,
        "tarjeta_ultimos4": last,
        "clave_operacion": data["clave_operacion"],
    }
    digest = fingerprint(signed)

    with engine().begin() as c:
        actor(c, {"cliente"})

        old_payment = c.execute(
            text(
                """
                SELECT id,suscripcion_id,solicitud_hash
                FROM pagos_suscripcion
                WHERE usuario_id=:usuario_id
                  AND clave_operacion=:clave
                """
            ),
            {"usuario_id": user_id, "clave": data["clave_operacion"]},
        ).mappings().first()

        if old_payment:
            if (
                old_payment["solicitud_hash"] != digest
                or old_payment["suscripcion_id"] != subscription_id
            ):
                raise ApiError(
                    "La clave_operacion ya se usó para otro contenido.", 409
                )
            result = subscription_json(c, subscription_id, user_id)
            result["pago"] = payment_json(c, old_payment["id"], user_id)
            result["pago_simulado"] = True
            result["cambio_realizado"] = False
            return response(result, message="Renovación ya registrada.")

        sub = c.execute(
            text("SELECT * FROM suscripciones WHERE id=:id FOR UPDATE"),
            {"id": subscription_id},
        ).mappings().first()
        if not sub:
            raise ApiError("Suscripción no encontrada.", 404)
        if sub["usuario_id"] != user_id:
            raise ApiError("La suscripción no pertenece al cliente.", 403)
        if sub["estado"] in ("cancelada", "suspendida"):
            raise ApiError(
                "La suscripción no puede renovarse en su estado actual.", 409
            )

        plan_active = c.execute(
            text("SELECT activo FROM planes_suscripcion WHERE id=:id"),
            {"id": sub["plan_id"]},
        ).scalar_one_or_none()
        if plan_active != 1:
            raise ApiError("El plan ya no permite renovaciones.", 409)

        period = c.execute(
            text(
                """
                SELECT
                    IF(:fecha_fin>NOW(),:fecha_fin,NOW()) AS inicio,
                    DATE_ADD(
                        IF(:fecha_fin>NOW(),:fecha_fin,NOW()),
                        INTERVAL :meses MONTH
                    ) AS fin
                """
            ),
            {
                "fecha_fin": sub["fecha_fin"],
                "meses": sub["duracion_meses_contratada"],
            },
        ).mappings().one()

        c.execute(
            text(
                """
                UPDATE suscripciones
                SET fecha_fin=:fin,
                    estado='activa',
                    fecha_cancelacion=NULL,
                    motivo_cancelacion=NULL
                WHERE id=:id
                """
            ),
            {"fin": period["fin"], "id": subscription_id},
        )

        reference = "DEMO-" + uuid.uuid4().hex[:20].upper()
        payment_id = c.execute(
            text(
                """
                INSERT INTO pagos_suscripcion(
                    suscripcion_id,usuario_id,periodo_inicio,periodo_fin,
                    monto,metodo_pago,estado,tarjeta_ultimos4,
                    referencia_pago,clave_operacion,solicitud_hash,fecha_pago
                )
                VALUES(
                    :suscripcion_id,:usuario_id,:inicio,:fin,
                    :monto,:metodo,'aprobado',:ultimos4,
                    :referencia,:clave,:hash,NOW()
                )
                """
            ),
            {
                "suscripcion_id": subscription_id,
                "usuario_id": user_id,
                "inicio": period["inicio"],
                "fin": period["fin"],
                "monto": sub["precio_mensual_contratado"],
                "metodo": method,
                "ultimos4": last,
                "referencia": reference,
                "clave": data["clave_operacion"],
                "hash": digest,
            },
        ).lastrowid

        result = subscription_json(c, subscription_id, user_id)
        result["pago"] = payment_json(c, payment_id, user_id)
        result["pago_simulado"] = True
        result["cambio_realizado"] = True

    return response(
        result,
        message="Suscripción renovada. No se realizó ningún cobro real.",
        status=201,
    )


@suscripciones.patch("/suscripciones/<int:subscription_id>/cancelar")
@requiere_roles("cliente")
@endpoint
def cancel(subscription_id):
    data = body({"motivo"}) if request.get_data() else {}
    reason = string(data.get("motivo"), "motivo", 255, True)
    user_id = g.usuario_actual["id"]

    with engine().begin() as c:
        actor(c, {"cliente"})
        sub = c.execute(
            text("SELECT usuario_id,estado FROM suscripciones WHERE id=:id FOR UPDATE"),
            {"id": subscription_id},
        ).mappings().first()
        if not sub:
            raise ApiError("Suscripción no encontrada.", 404)
        if sub["usuario_id"] != user_id:
            raise ApiError("La suscripción no pertenece al cliente.", 403)
        if sub["estado"] == "cancelada":
            result = subscription_json(c, subscription_id, user_id)
            result["cambio_realizado"] = False
            return response(result, message="La suscripción ya estaba cancelada.")
        if sub["estado"] == "suspendida":
            raise ApiError(
                "Una suscripción suspendida requiere revisión administrativa.", 409
            )

        c.execute(
            text(
                """
                UPDATE suscripciones
                SET estado='cancelada',
                    fecha_cancelacion=NOW(),
                    motivo_cancelacion=:motivo
                WHERE id=:id
                """
            ),
            {"id": subscription_id, "motivo": reason},
        )
        result = subscription_json(c, subscription_id, user_id)
        result["cambio_realizado"] = True

    return response(result, message="Suscripción cancelada.")


@suscripciones.get("/admin/suscripciones")
@requiere_roles("administrador")
@endpoint
def admin_subscriptions():
    allowed = ("estado", "usuario_id", "plan_id")
    query(allowed)
    g.query_allowed = allowed
    filters = []
    params = {}

    if "estado" in request.args:
        state = request.args["estado"]
        if state not in ("activa", "vencida", "cancelada", "suspendida"):
            raise ApiError("estado inválido.")
        filters.append("estado_efectivo=:estado")
        params["estado"] = state

    for field in ("usuario_id", "plan_id"):
        if field in request.args:
            try:
                value = int(request.args[field])
            except ValueError:
                raise ApiError(field + " inválido.") from None
            params[field] = integer(value, field)
            filters.append(field + "=:" + field)

    where = " AND ".join(filters) if filters else "1=1"
    with engine().connect() as c:
        return page(
            c,
            "SELECT * FROM vw_suscripciones_detalle WHERE "
            + where
            + " ORDER BY suscripcion_id DESC",
            params,
        )


@suscripciones.get("/admin/pagos-suscripcion")
@requiere_roles("administrador")
@endpoint
def admin_payments():
    with engine().connect() as c:
        return page(
            c,
            """
            SELECT p.id,p.suscripcion_id,p.usuario_id,u.nombre AS cliente,
                   p.periodo_inicio,p.periodo_fin,p.monto,p.metodo_pago,
                   p.estado,p.tarjeta_ultimos4,p.referencia_pago,
                   p.fecha_pago,p.fecha_creacion
            FROM pagos_suscripcion p
            JOIN usuarios u ON u.id=p.usuario_id
            ORDER BY p.id DESC
            """,
        )


@suscripciones.post("/admin/suscripciones/marcar-vencidas")
@requiere_roles("administrador")
@endpoint
def expire_subscriptions():
    if request.get_data():
        raise ApiError("No envíes cuerpo para esta operación.")
    with engine().begin() as c:
        actor(c, {"administrador"})
        result = c.execute(
            text(
                """
                UPDATE suscripciones
                SET estado='vencida'
                WHERE estado='activa' AND fecha_fin<=NOW()
                """
            )
        )
        total = result.rowcount
    return response({"suscripciones_actualizadas": total})


@suscripciones.get("/health/suscripciones")
@endpoint
def subscription_health():
    with engine().connect() as c:
        tables = c.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema=DATABASE()
                  AND table_name IN (
                    'planes_suscripcion','suscripciones','pagos_suscripcion'
                  )
                """
            )
        ).scalar_one()
        views = c.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.views
                WHERE table_schema=DATABASE()
                  AND table_name IN (
                    'vw_suscripciones_detalle','vw_suscripciones_activas'
                  )
                """
            )
        ).scalar_one()
        triggers = c.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.triggers
                WHERE trigger_schema=DATABASE()
                  AND trigger_name LIKE '%suscripcion%'
                """
            )
        ).scalar_one()

    state = {"tablas": tables, "vistas": views, "triggers": triggers}
    if tables != 3 or views != 2 or triggers < 9:
        return response(
            state,
            message="El módulo de suscripciones está incompleto.",
            status=503,
        )
    return response(state, message="Módulo de suscripciones verificado.")
