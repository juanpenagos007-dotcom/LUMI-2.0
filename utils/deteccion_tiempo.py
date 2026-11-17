
import re
import unicodedata

from services.tiempo_service import (
    obtener_hora,
    obtener_fecha,
    obtener_fecha_hora,
    obtener_hora_natural,
)


def normalizar_tiempo(texto):
    texto = unicodedata.normalize("NFD", str(texto or "").lower())
    texto = "".join(
        caracter for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )
    return re.sub(r"\s+", " ", texto).strip()


def detectar_consulta_tiempo(texto):
    """
    Devuelve una respuesta cuando se consulta
    la fecha u hora de Colombia.

    Devuelve None si no es una consulta temporal.
    """
    texto = normalizar_tiempo(texto)

    # Consultas sobre la hora actual.
    pregunta_hora = bool(re.search(
        r"\b(que hora es|que horas son|"
        r"dime la hora|decirme la hora|"
        r"me dices la hora|hora actual|"
        r"hora tenemos|hora es ahora|"
        r"me puedes decir la hora|"
        r"puedes decirme la hora|"
        r"me puedes decir que hora|"
        r"puedes decirme que hora|"
        r"me dices que hora|"
        r"la hora es|"
        r"que hora tenemos)\b",
        texto,
    ))

    # Consultas sobre la fecha actual.
    pregunta_fecha = bool(re.search(
        r"\b(que fecha es|fecha de hoy|"
        r"dime la fecha|decirme la fecha|"
        r"que dia es hoy|en que dia estamos|"
        r"en que mes estamos|que mes es|"
        r"que año es|en que año estamos)\b",
        texto,
    ))

    if not pregunta_hora and not pregunta_fecha:
        return None

    if pregunta_hora and pregunta_fecha:
        return f"💜 ¡Claro! {obtener_fecha_hora()}"

    if pregunta_hora:
        return f"💜 {obtener_hora_natural()}"

    return f"💜 ¡Hoy es {obtener_fecha()}!"
