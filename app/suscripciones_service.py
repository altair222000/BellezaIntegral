"""Reglas compartidas de beneficios de suscripción."""
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import text


def descuento_productos_activo(conexion, usuario_id, bloquear=False):
    """Devuelve el porcentaje de descuento de productos vigente."""
    if not usuario_id:
        return 0

    bloqueo = " FOR SHARE" if bloquear else ""
    valor = conexion.execute(
        text(
            """
            SELECT descuento_productos_contratado
            FROM suscripciones
            WHERE usuario_id=:usuario_id
              AND estado='activa'
              AND fecha_inicio<=NOW()
              AND fecha_fin>NOW()
            ORDER BY fecha_fin DESC, id DESC
            LIMIT 1
            """
            + bloqueo
        ),
        {"usuario_id": usuario_id},
    ).scalar_one_or_none()

    return int(valor or 0)


def precio_con_descuento(precio, porcentaje):
    """Aplica el porcentaje y redondea a centavos."""
    precio = Decimal(precio)
    porcentaje = Decimal(int(porcentaje or 0))
    factor = (Decimal("100") - porcentaje) / Decimal("100")
    return (precio * factor).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
