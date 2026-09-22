"""Pruebas unitarias de reglas que no requieren una base de datos."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from flask import Flask, g

from app.api_common import (
    ApiError,
    boolean,
    clean,
    date_value,
    integer,
    key,
    money,
    string,
)
from app.auth_service import autenticar_usuario, consultar_perfil
from app.db_context import actor_id_actual, ip_actual
from app.disponibilidad_service import (
    ZONA_NEGOCIO,
    unir_fecha_hora,
    validar_fecha,
)
from app.permisos import requiere_roles
from app.security import configurar_jwt
from app.servicios_service import validar_servicio
from app.usuarios_service import validar_registro


def test_validar_registro_normaliza_datos_validos():
    resultado = validar_registro(
        {
            "nombre": "  Ana López  ",
            "email": "  ANA@EXAMPLE.COM ",
            "telefono": " +50255550101 ",
            "password": "Secreta123",
        }
    )

    assert resultado == {
        "nombre": "Ana López",
        "email": "ana@example.com",
        "telefono": "+50255550101",
        "password": "Secreta123",
    }


@pytest.mark.parametrize(
    "datos",
    [
        None,
        {"nombre": "Ana", "email": "ana@example.com", "password": "1234567"},
        {"nombre": "Ana", "email": "correo-invalido", "password": "12345678"},
        {"nombre": "Ana", "telefono": "555-0101", "password": "12345678"},
        {"nombre": "Ana", "password": "12345678"},
        {
            "nombre": "Ana",
            "email": "ana@example.com",
            "password": "12345678",
            "rol": "administrador",
        },
    ],
)
def test_validar_registro_rechaza_entradas_invalidas(datos):
    with pytest.raises(ValueError):
        validar_registro(datos)


def test_validar_servicio_convierte_precio_y_normaliza_opcionales():
    resultado = validar_servicio(
        {
            "nombre": "  Manicura  ",
            "descripcion": "  Esmaltado tradicional  ",
            "categoria": "  Uñas ",
            "duracion_min": 60,
            "precio": "135",
            "imagen": "  /img/manicura.webp  ",
        }
    )

    assert resultado["nombre"] == "Manicura"
    assert resultado["descripcion"] == "Esmaltado tradicional"
    assert resultado["categoria"] == "Uñas"
    assert resultado["duracion_min"] == 60
    assert resultado["precio"] == Decimal("135.00")
    assert resultado["imagen"] == "/img/manicura.webp"


@pytest.mark.parametrize(
    "datos",
    [
        {
            "nombre": "Manicura",
            "categoria": "Uñas",
            "duracion_min": True,
            "precio": "135.00",
        },
        {
            "nombre": "Manicura",
            "categoria": "Uñas",
            "duracion_min": 60,
            "precio": "135.123",
        },
        {
            "nombre": "Manicura",
            "categoria": "Uñas",
            "duracion_min": 60,
            "precio": 135,
        },
        {
            "nombre": "Manicura",
            "categoria": "Uñas",
            "duracion_min": 60,
            "precio": "135.00",
            "campo_no_permitido": True,
        },
    ],
)
def test_validar_servicio_rechaza_entradas_invalidas(datos):
    with pytest.raises(ValueError):
        validar_servicio(datos)


def test_validadores_compartidos_aplican_limites_y_tipos():
    assert string("  Belleza  ", "nombre", 20) == "Belleza"
    assert string(None, "imagen", 255, optional=True) is None
    assert integer(10, "cantidad", 1, 10) == 10
    assert boolean(False) is False
    assert money("135") == Decimal("135.00")
    assert date_value("2026-09-22") == date(2026, 9, 22)
    assert key("pedido_001") == "pedido_001"


@pytest.mark.parametrize(
    "funcion, valor",
    [
        (lambda value: string(value, "nombre", 5), "      "),
        (lambda value: integer(value, "cantidad"), True),
        (lambda value: boolean(value), 1),
        (lambda value: money(value), "-1.00"),
        (lambda value: date_value(value), "2026-02-30"),
        (lambda value: key(value), "corta"),
    ],
)
def test_validadores_compartidos_rechazan_valores_fuera_de_regla(funcion, valor):
    with pytest.raises(ApiError):
        funcion(valor)


def test_clean_serializa_decimal_fechas_y_banderas():
    valor = clean(
        {
            "precio": Decimal("12.50"),
            "fecha": date(2026, 9, 22),
            "activo": 1,
            "items": (Decimal("2.00"),),
        }
    )

    assert valor == {
        "precio": "12.50",
        "fecha": "2026-09-22",
        "activo": True,
        "items": ["2.00"],
    }


def test_validar_fecha_exige_fecha_futura_y_formato_iso():
    manana = datetime.now(ZONA_NEGOCIO).date() + timedelta(days=1)

    assert validar_fecha(manana.isoformat()) == manana

    with pytest.raises(ValueError):
        validar_fecha("2026-02-30")
    with pytest.raises(ValueError):
        validar_fecha("22-09-2026")
    with pytest.raises(ValueError):
        validar_fecha((manana - timedelta(days=2)).isoformat())


def test_unir_fecha_hora_conserva_zona_horaria_del_negocio():
    momento = unir_fecha_hora(date(2026, 9, 23), "09:30:00")

    assert momento.hour == 9
    assert momento.minute == 30
    assert momento.tzinfo == ZONA_NEGOCIO


def test_autenticar_usuario_valida_entrada_antes_de_acceder_a_bd():
    with pytest.raises(ValueError):
        autenticar_usuario(None, {"identificador": 10, "password": "secreta"})

    with pytest.raises(ValueError):
        autenticar_usuario(
            None,
            {"identificador": "cliente@example.com", "password": "", "otro": 1},
        )

    assert consultar_perfil(None, "no-es-un-id") is None
    assert consultar_perfil(None, "0") is None


def test_contexto_de_bd_usa_usuario_e_ip_de_la_solicitud():
    aplicacion = Flask(__name__)

    assert actor_id_actual() is None
    assert ip_actual() is None

    with aplicacion.test_request_context(
        "/",
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    ):
        g.usuario_actual = {"id": 42}
        assert actor_id_actual() == 42
        assert ip_actual() == "192.0.2.10"

        g.usuario_actual = "valor-no-valido"
        assert actor_id_actual() is None


def test_configurar_jwt_rechaza_clave_insegura_y_configura_clave_valida(monkeypatch):
    aplicacion = Flask(__name__)

    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        configurar_jwt(aplicacion)

    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 64)
    configurar_jwt(aplicacion)

    assert aplicacion.config["JWT_SECRET_KEY"] == "x" * 64
    assert aplicacion.config["JWT_TOKEN_LOCATION"] == ["headers"]


def test_requiere_roles_solo_acepta_roles_del_sistema():
    with pytest.raises(ValueError):
        requiere_roles()

    with pytest.raises(ValueError):
        requiere_roles("superusuario")

    @requiere_roles("cliente")
    def endpoint_de_prueba():
        return "ok"

    assert endpoint_de_prueba.__name__ == "endpoint_de_prueba"
