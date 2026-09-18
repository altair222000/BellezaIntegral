import os
from datetime import timedelta

from flask import jsonify
from flask_jwt_extended import JWTManager


def configurar_jwt(app):
    clave = os.getenv("JWT_SECRET_KEY")

    if not clave or len(clave) < 64:
        raise RuntimeError(
            "Configura JWT_SECRET_KEY en .env con la clave generada."
        )

    app.config["JWT_SECRET_KEY"] = clave
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]

    jwt = JWTManager(app)

    def error_token(mensaje):
        return jsonify({
            "success": False,
            "message": mensaje,
            "data": None,
        }), 401

    @jwt.unauthorized_loader
    def token_ausente(motivo):
        return error_token("Debes iniciar sesión para acceder.")

    @jwt.invalid_token_loader
    def token_invalido(motivo):
        return error_token("El token no es válido.")

    @jwt.expired_token_loader
    def token_vencido(encabezado, contenido):
        return error_token("La sesión venció. Inicia sesión nuevamente.")

    @jwt.token_in_blocklist_loader
    def token_revocado(header, payload):
        from flask import current_app
        from sqlalchemy import text
        with current_app.extensions["db_engine"].connect() as c:
            revoked = c.execute(text("SELECT 1 FROM tokens_revocados WHERE jti=:jti"), {"jti":payload["jti"]}).first()
            version = c.execute(text("SELECT version FROM sesiones_usuario WHERE usuario_id=:id"), {"id":payload["sub"]}).scalar()
        return bool(revoked) or payload.get("version", 0) != (version or 0)

    @jwt.revoked_token_loader
    def sesion_revocada(header, payload):
        return error_token("La sesión fue cerrada. Inicia sesión nuevamente.")
