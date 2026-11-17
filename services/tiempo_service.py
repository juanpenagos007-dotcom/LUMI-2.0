
from datetime import datetime
from zoneinfo import ZoneInfo

ZONA_COLOMBIA = ZoneInfo("America/Bogota")

DIAS = [
    "lunes", "martes", "miércoles", "jueves",
    "viernes", "sábado", "domingo"
]

MESES = [
    "enero", "febrero", "marzo", "abril",
    "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre"
]


def obtener_hora():
    ahora = datetime.now(ZONA_COLOMBIA)

    hora = ahora.strftime("%I:%M").lstrip("0")
    periodo = "a. m." if ahora.hour < 12 else "p. m."

    return f"{hora} {periodo}"


def obtener_fecha():
    ahora = datetime.now(ZONA_COLOMBIA)

    dia = DIAS[ahora.weekday()]
    mes = MESES[ahora.month - 1]

    return f"{dia} {ahora.day} de {mes} de {ahora.year}"


def obtener_fecha_hora():
    return f"Hoy es {obtener_fecha()} y son las {obtener_hora()}."


# ============================================================
# LUMI 💜
# HORA NATURAL PARA RESPUESTAS HABLADAS
# ============================================================

NUMEROS_HORA = [
    "doce", "una", "dos", "tres", "cuatro", "cinco",
    "seis", "siete", "ocho", "nueve", "diez", "once",
]

UNIDADES = [
    "cero", "uno", "dos", "tres", "cuatro",
    "cinco", "seis", "siete", "ocho", "nueve",
]

ESPECIALES = {
    10: "diez",
    11: "once",
    12: "doce",
    13: "trece",
    14: "catorce",
    15: "quince",
    16: "dieciséis",
    17: "diecisiete",
    18: "dieciocho",
    19: "diecinueve",
    20: "veinte",
    21: "veintiuno",
    22: "veintidós",
    23: "veintitrés",
    24: "veinticuatro",
    25: "veinticinco",
    26: "veintiséis",
    27: "veintisiete",
    28: "veintiocho",
    29: "veintinueve",
}

DECENAS = {
    30: "treinta",
    40: "cuarenta",
    50: "cincuenta",
}


def numero_a_palabras(numero):
    if not isinstance(numero, int) or not 0 <= numero <= 59:
        raise ValueError("El número debe estar entre 0 y 59.")

    if numero < 10:
        return UNIDADES[numero]

    if numero in ESPECIALES:
        return ESPECIALES[numero]

    decena = (numero // 10) * 10
    unidad = numero % 10

    if unidad == 0:
        return DECENAS[decena]

    return f"{DECENAS[decena]} y {UNIDADES[unidad]}"


def obtener_hora_natural():
    ahora = datetime.now(ZONA_COLOMBIA)

    hora = ahora.hour
    minutos = ahora.minute

    if hora == 0 and minutos == 0:
        return "¡Es medianoche!"

    if hora == 12 and minutos == 0:
        return "¡Es mediodía!"

    hora_12 = hora % 12
    nombre_hora = NUMEROS_HORA[hora_12]

    if 5 <= hora < 12:
        periodo = "de la mañana"
    elif 12 <= hora < 19:
        periodo = "de la tarde"
    elif 19 <= hora <= 23:
        periodo = "de la noche"
    else:
        periodo = "de la madrugada"

    inicio = "Es la" if hora_12 == 1 else "Son las"

    if minutos == 0:
        return f"¡{inicio} {nombre_hora} {periodo}!"

    if minutos == 30:
        return f"¡{inicio} {nombre_hora} y media {periodo}!"

    if minutos == 15:
        return f"¡{inicio} {nombre_hora} y cuarto {periodo}!"

    minutos_texto = numero_a_palabras(minutos)

    return (
        f"¡{inicio} {nombre_hora} y "
        f"{minutos_texto} {periodo}!"
    )
