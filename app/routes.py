from flask import Blueprint, current_app, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

api = Blueprint("api", __name__, url_prefix="/api/v1")


@api.get("/health")
def verificar_api():
    return jsonify({
        "success": True,
        "message": "API Belleza Integral disponible",
        "data": {
            "api": "ok"
        }
    }), 200


@api.get("/health/db")
def verificar_base_datos():
    motor = current_app.extensions["db_engine"]

    try:
        with motor.connect() as conexion:
            conexion.execute(text("SELECT 1"))

    except SQLAlchemyError:
        # No enviamos credenciales ni detalles internos al cliente.
        current_app.logger.error(
            "No fue posible verificar la conexión con MySQL."
        )

        return jsonify({
            "success": False,
            "message": "Base de datos no disponible",
            "data": None
        }), 503

    return jsonify({
        "success": True,
        "message": "Conexión con MySQL verificada",
        "data": {
            "database": "ok"
        }
    }), 200

@api.get("/health/schema")
def verificar_esquema():
    motor = current_app.extensions["db_engine"]
    try:
        with motor.connect() as conexion:
            tablas = conexion.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema=DATABASE()
                  AND table_name IN ('auditoria_cambios','auditoria_eventos')
            """)).scalar_one()
            vistas = conexion.execute(text("""
                SELECT COUNT(*) FROM information_schema.views
                WHERE table_schema=DATABASE()
                  AND table_name IN ('vw_citas_detalle','vw_inventario_actual',
                                     'vw_resumen_pedidos','vw_clientes_fidelizacion',
                                     'vw_promociones_vigentes')
            """)).scalar_one()
            triggers = conexion.execute(text("""
                SELECT COUNT(*) FROM information_schema.triggers
                WHERE trigger_schema=DATABASE()
            """)).scalar_one()
            rutinas = conexion.execute(text("""
                SELECT COUNT(*) FROM information_schema.routines
                WHERE routine_schema=DATABASE()
                  AND routine_name IN (
                    'sp_registrar_movimiento_inventario','sp_ajustar_puntos',
                    'sp_crear_cita','sp_asignar_personal_cita',
                    'sp_actualizar_estado_cita','sp_confirmar_pedido',
                    'sp_cancelar_pedido','fn_total_pedido',
                    'fn_stock_suficiente','fn_saldo_puntos'
                  )
            """)).scalar_one()
    except SQLAlchemyError:
        current_app.logger.error("No fue posible verificar el esquema MySQL.")
        return jsonify({"success":False,"message":"No fue posible verificar el esquema","data":None}),503

    ok = tablas == 2 and vistas == 5 and triggers >= 40 and rutinas == 10
    estado = {"tablas_auditoria":tablas,"vistas":vistas,"triggers":triggers,"rutinas":rutinas}
    if not ok:
        return jsonify({"success":False,"message":"La capa de integridad está incompleta","data":estado}),503
    return jsonify({"success":True,"message":"Esquema de integridad verificado","data":estado}),200
