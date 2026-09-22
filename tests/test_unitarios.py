from datetime import datetime, timedelta

import pytest
from werkzeug.datastructures import MultiDict

from app.admin_service import validar_filtros_citas
from app.agenda_service import validar_fecha_agenda
from app.citas_service import validar_cita
from app.disponibilidad_service import ZONA_NEGOCIO
from app.fidelizacion_routes import validar_promocion
from app.tienda_routes import validar_producto
from app.usuarios_service import validar_registro


def fecha_futura():
    return (datetime.now(ZONA_NEGOCIO).date() + timedelta(days=7)).isoformat()


def test_validar_registro_normaliza_correo():
    resultado = validar_registro({
        "nombre": "  Cliente Prueba  ",
        "email": "CLIENTE@EXAMPLE.COM",
        "telefono": None,
        "password": "Password2026!",
    })
    assert resultado["nombre"] == "Cliente Prueba"
    assert resultado["email"] == "cliente@example.com"
    assert resultado["telefono"] is None


@pytest.mark.parametrize("datos", [
    {"nombre": "Cliente", "password": "Password2026!"},
    {"nombre": "Cliente", "email": "correo-invalido", "password": "Password2026!"},
    {"nombre": "Cliente", "telefono": "123", "password": "Password2026!"},
    {"nombre": "Cliente", "email": "a@example.com", "password": "123"},
])
def test_validar_registro_rechaza_datos_invalidos(datos):
    with pytest.raises(ValueError):
        validar_registro(datos)


def test_validar_cita_acepta_datos_coherentes():
    resultado = validar_cita({
        "personal_id": 3,
        "servicio_id": 1,
        "fecha": fecha_futura(),
        "hora": "09:30",
        "notas": "Primera visita",
    })
    assert resultado["personal_id"] == 3
    assert resultado["servicio_id"] == 1
    assert resultado["hora"] == "09:30"


@pytest.mark.parametrize("campo,valor", [
    ("personal_id", 0),
    ("servicio_id", "1"),
    ("hora", "25:00"),
])
def test_validar_cita_rechaza_identificadores_y_horas_invalidas(campo, valor):
    datos = {
        "personal_id": 3,
        "servicio_id": 1,
        "fecha": fecha_futura(),
        "hora": "10:00",
    }
    datos[campo] = valor
    with pytest.raises(ValueError):
        validar_cita(datos)


def test_validar_promocion_controla_fechas_y_puntos():
    hoy = datetime.now(ZONA_NEGOCIO).date()
    resultado = validar_promocion({
        "titulo": "Beneficio fidelidad",
        "descripcion": "Canje válido en el salón",
        "descuento_porcentaje": 10,
        "fecha_inicio": hoy.isoformat(),
        "fecha_fin": (hoy + timedelta(days=30)).isoformat(),
        "puntos_costo": 100,
    })
    assert resultado["puntos_costo"] == 100

    with pytest.raises(Exception):
        validar_promocion({
            "titulo": "Inválida",
            "descripcion": "Fechas invertidas",
            "descuento_porcentaje": 10,
            "fecha_inicio": (hoy + timedelta(days=2)).isoformat(),
            "fecha_fin": hoy.isoformat(),
            "puntos_costo": 10,
        })


def test_validar_producto_aplica_regla_de_insumos():
    venta = validar_producto({
        "nombre": "Esmalte",
        "descripcion": "Color de prueba",
        "categoria": "Belleza",
        "tipo": "venta",
        "precio": "25.00",
        "imagen": None,
    })
    assert str(venta["precio"]) == "25.00"

    with pytest.raises(Exception):
        validar_producto({
            "nombre": "Algodón",
            "descripcion": None,
            "categoria": "Insumos",
            "tipo": "insumo",
            "precio": "10.00",
            "imagen": None,
        })


def test_validar_filtros_citas_acepta_y_rechaza_parametros():
    filtros, pagina, limite = validar_filtros_citas(
        MultiDict([("estado", "pendiente"), ("pagina", "2"), ("limite", "25")])
    )
    assert filtros["estado"] == "pendiente"
    assert pagina == 2
    assert limite == 25

    with pytest.raises(ValueError):
        validar_filtros_citas(MultiDict([("estado", "desconocido")]))


def test_validar_fecha_agenda():
    assert validar_fecha_agenda("2026-12-31").isoformat() == "2026-12-31"
    with pytest.raises(ValueError):
        validar_fecha_agenda("31/12/2026")
