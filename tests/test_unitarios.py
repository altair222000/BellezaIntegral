from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.api_common import ApiError, boolean, integer, key, money, string
from app.disponibilidad_service import ZONA_NEGOCIO, validar_fecha
from app.personal_service import validar_horario
from app.servicios_service import validar_servicio
from app.usuarios_service import validar_registro


def test_validar_registro_normaliza_cliente():
    datos = validar_registro({
        "nombre": "  Ana López  ",
        "email": "  ANA@EXAMPLE.COM ",
        "telefono": None,
        "password": "Password2026!",
    })

    assert datos["nombre"] == "Ana López"
    assert datos["email"] == "ana@example.com"
    assert datos["telefono"] is None


@pytest.mark.parametrize(
    "datos",
    [
        {"nombre": "Ana", "email": None, "telefono": None, "password": "Password2026!"},
        {"nombre": "", "email": "ana@example.com", "telefono": None, "password": "Password2026!"},
        {"nombre": "Ana", "email": "correo-invalido", "telefono": None, "password": "Password2026!"},
        {"nombre": "Ana", "email": None, "telefono": "123", "password": "Password2026!"},
        {"nombre": "Ana", "email": "ana@example.com", "telefono": None, "password": "123"},
    ],
)
def test_validar_registro_rechaza_datos_invalidos(datos):
    with pytest.raises(ValueError):
        validar_registro(datos)


def test_validar_servicio_conserva_precision_decimal():
    servicio = validar_servicio({
        "nombre": "Manicura clásica",
        "descripcion": "Servicio de prueba",
        "categoria": "Uñas",
        "duracion_min": 60,
        "precio": "135.50",
        "imagen": "manicura.jpg",
    })

    assert servicio["duracion_min"] == 60
    assert servicio["precio"] == Decimal("135.50")


@pytest.mark.parametrize("duracion", [True, False, 0, -1, 65536])
def test_validar_servicio_rechaza_duracion_invalida(duracion):
    with pytest.raises(ValueError):
        validar_servicio({
            "nombre": "Manicura",
            "categoria": "Uñas",
            "duracion_min": duracion,
            "precio": "100.00",
        })


def test_validar_horario_correcto():
    horario = validar_horario({
        "dia_semana": 1,
        "hora_inicio": "09:00",
        "hora_fin": "17:00",
    })

    assert horario == {
        "dia_semana": 1,
        "hora_inicio": "09:00",
        "hora_fin": "17:00",
    }


@pytest.mark.parametrize(
    "datos",
    [
        {"dia_semana": 0, "hora_inicio": "09:00", "hora_fin": "17:00"},
        {"dia_semana": 8, "hora_inicio": "09:00", "hora_fin": "17:00"},
        {"dia_semana": 1, "hora_inicio": "17:00", "hora_fin": "09:00"},
        {"dia_semana": 1, "hora_inicio": "9:00", "hora_fin": "17:00"},
    ],
)
def test_validar_horario_rechaza_conflictos(datos):
    with pytest.raises(ValueError):
        validar_horario(datos)


def test_validadores_comunes_api():
    assert money("125.5") == Decimal("125.50")
    assert integer(5, "cantidad", 1, 10) == 5
    assert boolean(True) is True
    assert string("  válido  ", "nombre", 20) == "válido"
    assert key("operacion_2026") == "operacion_2026"


@pytest.mark.parametrize("valor", [True, False, 0, -1, 11, "5"])
def test_integer_rechaza_tipos_y_limites(valor):
    with pytest.raises(ApiError):
        integer(valor, "cantidad", 1, 10)


def test_validar_fecha_futura():
    fecha = datetime.now(ZONA_NEGOCIO).date() + timedelta(days=1)
    assert validar_fecha(fecha.isoformat()) == fecha


@pytest.mark.parametrize("valor", ["2026/09/21", "2026-02-30", "", None])
def test_validar_fecha_rechaza_formato_o_fecha_inexistente(valor):
    with pytest.raises(ValueError):
        validar_fecha(valor)
