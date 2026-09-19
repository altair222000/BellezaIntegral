from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify

from .database import crear_motor
from .routes import api
from .auth_routes import auth
from .security import configurar_jwt
from .admin_routes import admin
from .servicios_routes import servicios
from .personal_routes import personal
from .disponibilidad_routes import disponibilidad
from .citas_routes import citas
from .agenda_routes import agenda

def create_app():
    raiz = Path(__file__).resolve().parent.parent
    load_dotenv(raiz / ".env")

    app = Flask(__name__)
    app.json.ensure_ascii = False
    configurar_jwt(app)
    app.extensions["db_engine"] = crear_motor()
    app.register_blueprint(api)
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(servicios)
    app.register_blueprint(personal)
    app.register_blueprint(disponibilidad)
    app.register_blueprint(citas)
    app.register_blueprint(agenda)

    @app.errorhandler(404)
    def ruta_no_encontrada(error):
        return jsonify({
            "success": False,
            "message": "Ruta no encontrada",
            "data": None
        }), 404

    from .tienda_routes import tienda
    from .fidelizacion_routes import fidelizacion
    from .cuentas_routes import cuentas
    from .horarios_routes import horarios
    from .reportes_routes import reportes
    from .visor_routes import visor
    from .auditoria_routes import auditoria
    from .suscripciones_routes import suscripciones
    from .integracion import configurar_integracion
    for blueprint in (tienda, fidelizacion, cuentas, horarios, reportes, visor, auditoria, suscripciones):
        app.register_blueprint(blueprint)
    configurar_integracion(app)
    return app