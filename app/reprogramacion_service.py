"""Disponibilidad privada; la escritura conserva sus comprobaciones transaccionales."""
from datetime import datetime
from sqlalchemy import text
from .api_common import ApiError, integer
from .disponibilidad_service import (
    calcular_disponibilidad, RecursoNoDisponible, unir_fecha_hora, ZONA_NEGOCIO,
)


def horarios_para_reprogramar(motor, cliente_id, cita_id, argumentos):
    integer(cita_id, 'cita_id')
    if set(argumentos) != {'fecha'} or len(argumentos.getlist('fecha')) != 1:
        raise ApiError('Envía únicamente fecha, una sola vez, con formato YYYY-MM-DD.')
    with motor.connect() as c:
        cita = c.execute(text("""
            SELECT id,personal_id,servicio_id,duracion_min,fecha,
                   TIME_FORMAT(hora,'%H:%i:%s') AS hora,estado
            FROM citas WHERE id=:id AND cliente_id=:cliente
        """), {'id':cita_id,'cliente':cliente_id}).mappings().first()
    if not cita:
        raise ApiError('Cita no encontrada.',404)
    if cita['estado'] not in ('pendiente','confirmada'):
        raise ApiError('Esta cita ya no se puede reprogramar.',409)
    if unir_fecha_hora(cita['fecha'],cita['hora']) <= datetime.now(ZONA_NEGOCIO):
        raise ApiError('La cita ya comenzó o su fecha pasó.',409)
    try:
        resultado = calcular_disponibilidad(
            motor,cita['personal_id'],cita['servicio_id'],argumentos['fecha'],
            cita_excluida=cita_id,cliente_id=cliente_id,duracion_reserva=cita['duracion_min'],
        )
    except RecursoNoDisponible as exc:
        raise ApiError(str(exc),404) from None
    return {**resultado,'cita_id':cita_id}
