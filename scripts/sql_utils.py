"""Utilidades mínimas para ejecutar scripts MySQL con DELIMITER."""
from pathlib import Path


def dividir_script_mysql(texto: str):
    delimitador = ";"
    acumulado = []

    for linea in texto.splitlines():
        limpia = linea.strip()
        if limpia.upper().startswith("DELIMITER "):
            if acumulado and "".join(acumulado).strip():
                raise ValueError("Cambio de DELIMITER con una sentencia incompleta.")
            delimitador = limpia.split(None, 1)[1]
            continue

        acumulado.append(linea + "\n")
        contenido = "".join(acumulado).rstrip()
        if contenido.endswith(delimitador):
            sentencia = contenido[: -len(delimitador)].strip()
            acumulado = []
            if sentencia:
                yield sentencia

    restante = "".join(acumulado).strip()
    if restante:
        yield restante


def cargar_sentencias(ruta):
    return list(dividir_script_mysql(Path(ruta).read_text(encoding="utf-8-sig")))
