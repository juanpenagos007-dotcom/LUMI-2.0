# ============================================================
# LUMI 💜
# DETECCIÓN DE SOLICITUDES DE AUDIO Y TEXTO
# ============================================================

import re

from utils.texto import normalizar


# ============================================================
# NOMBRES Y SALUDOS
# ============================================================

PREFIJO = (
    r"^(?:(?:oye|hola|hey|buenas)\s+)?"
    r"(?:(?:lumi|l u m i|lightby|light by|lightboy)"
    r"\s+)?"
    r"(?:(?:por favor)\s+)?"
)


def limpiar_prefijo(texto):
    """Elimina saludos y nombres al comienzo del mensaje."""
    return re.sub(PREFIJO, "", texto).strip()


# ============================================================
# PREFERENCIAS EXPLÍCITAS DE TEXTO
# ============================================================

PATRONES_SOLO_TEXTO = [
    r"\bno (?:me )?(?:mandes|envies|respondas|"
    r"contestes|hables|expliques)\b.{0,45}"
    r"\b(?:audio|voz|hablando)\b",

    r"\b(?:sin audio|solo texto|solamente texto|"
    r"por escrito|no quiero audio|no uses tu voz)\b",

    r"\b(?:prefiero|quiero|necesito)\b"
    r".{0,25}\b(?:texto|escrito)\b",

    r"\b(?:no hace falta|no necesito)\b"
    r".{0,25}\b(?:audio|voz)\b",
]


def solicita_solo_texto(texto):
    """Determina si el usuario prohíbe o descarta el audio."""
    texto = normalizar(texto)

    return any(
        re.search(patron, texto)
        for patron in PATRONES_SOLO_TEXTO
    )


# ============================================================
# PATRONES DE SOLICITUDES HABLADAS
# ============================================================

MODALIDAD_AUDIO = (
    r"(?:en\s+(?:un\s+)?audio|"
    r"con\s+(?:tu\s+)?voz|"
    r"por\s+(?:audio|voz)|"
    r"hablando|"
    r"en\s+(?:una\s+)?nota\s+de\s+voz)"
)

VERBOS_RESPUESTA = (
    r"(?:dime|cuentame|explicame|respondeme|"
    r"contestame|responde|contesta|"
    r"hablame|leeme|di|explica|cuenta)"
)

PATRONES_AUDIO = [
    # Explícame en un audio qué es Python.
    rf"\b{VERBOS_RESPUESTA}\s+{MODALIDAD_AUDIO}\b",

    # Explícame qué es Python, pero en audio.
    rf"\b(?:pero\s+)?{MODALIDAD_AUDIO}\s*$",

    # Quiero que me respondas con tu voz.
    rf"\b(?:quiero|necesito|prefiero|me gustaria)"
    rf"\s+(?:que\s+)?(?:me\s+)?"
    rf"(?:respondas|contestes|expliques|digas|"
    rf"cuentes|hables)\s+{MODALIDAD_AUDIO}\b",

    # ¿Puedes explicarme por voz qué es React?
    rf"\b(?:puedes|podrias)\s+"
    rf"(?:decirme|explicarme|responderme|"
    rf"contestarme|contarme|hablarme|leerme)"
    rf"\s+{MODALIDAD_AUDIO}\b",

    # Mándame un audio explicando JavaScript.
    r"\b(?:mandame|enviame|pasame|envia)\s+"
    r"(?:un\s+|una\s+)?"
    r"(?:audio|nota\s+de\s+voz|"
    r"mensaje\s+de\s+voz|mensaje\s+de\s+audio)\b",

    # Quiero escucharte explicar qué es una API.
    r"\b(?:quiero|me gustaria|prefiero)\s+"
    r"(?:escucharte|oirte)\s+"
    r"(?:explicar|contar|decir|hablar|responder)\b",

    # Háblame sobre inteligencia artificial.
    r"^hablame\s+(?:sobre|acerca de|de)\s+",

    # Dame una explicación hablada.
    r"\b(?:dame|quiero|necesito)\s+"
    r"(?:una?\s+)?"
    r"(?:respuesta|explicacion|mensaje)\s+"
    r"(?:en\s+audio|hablada|por\s+voz)\b",

    # Respóndeme por audio.
    rf"\b{VERBOS_RESPUESTA}\s+por\s+audio\b",

    # ¿Me lo puedes decir hablando?
    r"\b(?:me lo puedes decir|"
    r"puedes decirmelo|dimelo|dilo|"
    r"cuentamelo)\s+"
    r"(?:hablando|en audio|con tu voz)\b",
]


# ============================================================
# EXTRAER SOLICITUD DE AUDIO
# ============================================================

def extraer_peticion_audio(texto):
    """
    Detecta si un mensaje escrito solicita una respuesta
    hablada y extrae el contenido para Gemini.

    Devuelve:
        None -> No se solicitó audio.
        ""   -> Se solicitó audio sin indicar tema.
        str  -> Contenido para responder mediante voz.

    Ejemplos:
        "Lumi, explícame en audio qué es Python"
        -> "que es python"

        "Lumi, mándame un audio"
        -> ""

        "Cómo funciona el audio de Windows"
        -> None
    """

    texto = normalizar(texto)

    if not texto:
        return None

    texto = limpiar_prefijo(texto)

    # Una instrucción explícita de texto tiene prioridad.
    if solicita_solo_texto(texto):
        return None

    coincidencias = []

    for patron in PATRONES_AUDIO:
        coincidencia = re.search(patron, texto)

        if coincidencia:
            coincidencias.append(coincidencia)

    if not coincidencias:
        return None

    # Elegir el patrón que más texto cubre.
    coincidencia = max(
        coincidencias,
        key=lambda item: item.end() - item.start(),
    )

    # Quitar la instrucción de modalidad.
    contenido = (
        texto[:coincidencia.start()]
        + " "
        + texto[coincidencia.end():]
    )

    contenido = re.sub(r"\s+", " ", contenido).strip()

    # Quitar conectores sobrantes.
    contenido = re.sub(
        r"^(?:sobre|acerca de)\s+",
        "",
        contenido,
    )

    contenido = re.sub(
        r"^(?:por favor|quiero saber|"
        r"me gustaria saber)\s+",
        "",
        contenido,
    )

    # "Explícame qué es Python" puede quedar como
    # "que es python", lo cual Gemini comprende.
    return contenido.strip(" :,.¿?¡!")


# ============================================================
# RECUPERAR RESPUESTAS ANTERIORES
# ============================================================

PATRONES_ANTERIOR_TEXTO = [
    r"\b(?:escribeme|escribe|pasame|mandame|"
    r"enviame)\b.{0,50}"
    r"\b(?:ultimo|respuesta|dijiste|"
    r"anterior|eso|lo mismo)\b",

    r"\b(?:no entendi|no comprendi)\b"
    r".{0,50}\b(?:escribe|texto|escrito)\b",

    r"\b(?:lo ultimo|respuesta anterior|"
    r"lo que dijiste|eso)\b"
    r".{0,35}\b(?:texto|escrito)\b",

    r"^(?:mejor\s+)?(?:escribemelo|"
    r"pasamelo por escrito|dimelo por escrito)$",
]


PATRONES_ANTERIOR_AUDIO = [
    r"\b(?:repite|repiteme|repetir)\b"
    r".{0,50}\b(?:ultimo|respuesta|"
    r"dijiste|anterior|otra vez|audio|voz)\b",

    r"^(?:repite|repiteme|otra vez|"
    r"puedes repetir|repitelo)$",

    r"\b(?:vuelve a decir|dimelo otra vez|"
    r"dilo otra vez)\b",

    r"\b(?:leeme|lee|dime|cuentame|"
    r"repiteme)\b.{0,45}"
    r"\b(?:ultimo|anterior|respuesta|"
    r"eso|lo mismo|lo que dijiste)\b"
    r".{0,35}\b(?:audio|voz|hablando)\b",

    r"\b(?:lo ultimo|respuesta anterior|"
    r"lo que dijiste|eso|lo mismo)\b"
    r".{0,35}\b(?:audio|voz|hablando)\b",

    r"^(?:leemelo|dimelo en audio|"
    r"dimelo con tu voz|"
    r"repitelo en audio|"
    r"leeme eso|"
    r"quiero escucharlo|"
    r"quiero oirlo)$",
]


def detectar_peticion_anterior(texto):
    """
    Detecta solicitudes para repetir la última respuesta.

    Devuelve:
        "texto" -> Recuperar respuesta escrita.
        "audio" -> Recuperar respuesta hablada.
        None    -> No se solicitó repetición.
    """

    texto = limpiar_prefijo(normalizar(texto))

    if not texto:
        return None

    for patron in PATRONES_ANTERIOR_TEXTO:
        if re.search(patron, texto):
            return "texto"

    for patron in PATRONES_ANTERIOR_AUDIO:
        if re.search(patron, texto):
            return "audio"

    return None
