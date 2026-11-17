# ============================================================
# LUMI 💜
# FORMATO DE RESULTADOS DEL ANÁLISIS EMOCIONAL
# ============================================================

import math
import re

from config import MAX_ANALISIS

from data.analisis_config import (
    ANALISIS,
    EMOJIS_EMOCION,
    NOMBRES_EMOCION,
    NOMBRES_INTENCION,
)

from utils.texto import (
    escapar,
    elegir_texto,
    normalizar,
)


# ============================================================
# CONVERSIÓN DE VALORES
# ============================================================

def convertir_numero(valor, predeterminado=0.0):
    """Convierte valores numéricos de forma segura."""

    try:
        numero = float(valor)

        if not math.isfinite(numero):
            return predeterminado

        return numero

    except (TypeError, ValueError):
        return predeterminado


def convertir_porcentaje(valor):
    """
    Convierte una probabilidad a porcentaje.

    Admite valores entre 0 y 1, o porcentajes
    entre 0 y 100.
    """

    numero = convertir_numero(valor)

    if 0 <= numero <= 1:
        numero *= 100

    return max(0.0, min(numero, 100.0))


def normalizar_etiqueta(valor):
    """Normaliza nombres de categorías del modelo."""

    return normalizar(str(valor or "")).replace(" ", "_")


# ============================================================
# CONFIANZA DEL MODELO
# ============================================================

def obtener_confianza(confianza):
    """
    Devuelve la confianza estimada en porcentaje.

    No representa una garantía de exactitud.
    """

    return convertir_porcentaje(confianza)


# ============================================================
# TOXICIDAD
# ============================================================


def obtener_toxicidad(toxicidad):
    """
    Interpreta el indicador de toxicidad.

    Acepta las etiquetas del clasificador de Rubiela,
    otras etiquetas de texto y valores numéricos.
    """

    if isinstance(toxicidad, str):
        etiqueta = normalizar_etiqueta(toxicidad)

        etiquetas = {
            "si": "Posibles señales de lenguaje tóxico",
            "no": "Sin toxicidad evidente",
            "toxico": "Posible lenguaje tóxico",
            "toxica": "Posible lenguaje tóxico",
            "no_toxico": "Sin toxicidad evidente",
            "no_toxica": "Sin toxicidad evidente",
            "neutral": "Sin toxicidad evidente",
            "leve": "Posible toxicidad leve",
            "moderado": "Posible toxicidad moderada",
            "moderada": "Posible toxicidad moderada",
            "alto": "Posible toxicidad alta",
            "alta": "Posible toxicidad alta",
        }

        if etiqueta in etiquetas:
            return etiquetas[etiqueta]

    porcentaje = convertir_porcentaje(toxicidad)

    if porcentaje >= 75:
        return "Posible toxicidad alta"

    if porcentaje >= 45:
        return "Posible toxicidad moderada"

    if porcentaje >= 20:
        return "Posible toxicidad leve"

    return "Sin toxicidad evidente"



# ============================================================
# INDICADOR DE RIESGO
# ============================================================

def obtener_riesgo(riesgo):
    """
    Presenta un indicador orientativo de riesgo.

    No equivale a una evaluación profesional.
    """

    if isinstance(riesgo, str):
        etiqueta = normalizar_etiqueta(riesgo)

        etiquetas = {
            "bajo": "Bajo",
            "medio": "Medio",
            "moderado": "Moderado",
            "alto": "Alto",
            "critico": "Elevado",
            "ninguno": "No identificado",
        }

        if etiqueta in etiquetas:
            return etiquetas[etiqueta]

    porcentaje = convertir_porcentaje(riesgo)

    if porcentaje >= 75:
        return "Alto"

    if porcentaje >= 40:
        return "Moderado"

    if porcentaje >= 15:
        return "Bajo"

    return "No identificado"


# ============================================================
# INDICADOR DE EVASIÓN O GHOSTING
# ============================================================

def obtener_evasion(ghosting):
    """
    Interpreta el indicador de posible evasión.

    No permite confirmar las intenciones de alguien.
    """

    if isinstance(ghosting, str):
        etiqueta = normalizar_etiqueta(ghosting)

        etiquetas = {
            "si": "Posibles señales de evasión",
            "no": "Sin señales claras de evasión",
            "alto": "Posibles señales de evasión",
            "medio": "Señales ambiguas",
            "bajo": "Sin señales claras de evasión",
        }

        if etiqueta in etiquetas:
            return etiquetas[etiqueta]

    porcentaje = convertir_porcentaje(ghosting)

    if porcentaje >= 70:
        return "Posibles señales de evasión"

    if porcentaje >= 35:
        return "Señales ambiguas"

    return "Sin señales claras de evasión"


# ============================================================
# OBTENER INFORMACIÓN DE UNA INTENCIÓN
# ============================================================

def obtener_configuracion_intencion(intencion):
    """Busca la configuración de la intención detectada."""

    clave = normalizar_etiqueta(intencion)

    return ANALISIS.get(
        clave,
        ANALISIS.get("normal", {}),
    )


def obtener_nombre_emocion(emocion):
    """Obtiene el nombre legible de una emoción."""

    clave = normalizar_etiqueta(emocion)

    return NOMBRES_EMOCION.get(
        clave,
        str(emocion or "No determinada").capitalize(),
    )


def obtener_nombre_intencion(intencion):
    """Obtiene el nombre legible de una intención."""

    clave = normalizar_etiqueta(intencion)

    return NOMBRES_INTENCION.get(
        clave,
        str(intencion or "No determinada").capitalize(),
    )


# ============================================================
# FORMATO ESCRITO DEL ANÁLISIS
# ============================================================

def formatear_analisis(
    texto,
    emocion,
    toxicidad,
    ghosting,
    riesgo,
    intencion,
    confianza,
):
    """
    Genera un informe HTML para Telegram.

    Recibe los resultados de analizar_texto()
    y devuelve un texto listo para enviar
    con ParseMode.HTML.
    """

    clave_emocion = normalizar_etiqueta(emocion)

    emoji_emocion = EMOJIS_EMOCION.get(
        clave_emocion,
        "💬",
    )

    nombre_emocion = obtener_nombre_emocion(emocion)
    nombre_intencion = obtener_nombre_intencion(intencion)

    configuracion = obtener_configuracion_intencion(
        intencion
    )

    emoji_intencion = configuracion.get(
        "emoji",
        "💜",
    )

    titulo = configuracion.get(
        "titulo",
        "Análisis del mensaje",
    )

    introduccion = configuracion.get(
        "introduccion",
        "Este mensaje puede tener distintas interpretaciones.",
    )

    interpretacion = elegir_texto(
        configuracion.get("interpretaciones", [])
    )

    sugerencia = elegir_texto(
        configuracion.get("sugerencias", [])
    )

    confianza_porcentaje = obtener_confianza(
        confianza
    )

    texto_original = str(texto or "").strip()

    if len(texto_original) > MAX_ANALISIS:
        texto_original = (
            texto_original[:MAX_ANALISIS - 3] + "..."
        )

    partes = [
        "💜 <b>LUMI | ANÁLISIS DEL MENSAJE</b>",
        "",
        "<b>Mensaje analizado:</b>",
        escapar(texto_original),
        "",
        f"{escapar(emoji_intencion)} "
        f"<b>{escapar(titulo)}</b>",
        escapar(introduccion),
        "",
        "<b>Resultados del modelo:</b>",
        f"{emoji_emocion} <b>Emoción:</b> "
        f"{escapar(nombre_emocion)}",
        f"🎯 <b>Intención:</b> "
        f"{escapar(nombre_intencion)}",
        f"📊 <b>Confianza estimada:</b> "
        f"{confianza_porcentaje:.1f}%",
        f"🛡️ <b>Toxicidad:</b> "
        f"{escapar(obtener_toxicidad(toxicidad))}",
        f"🔎 <b>Evasión:</b> "
        f"{escapar(obtener_evasion(ghosting))}",
        f"⚠️ <b>Riesgo:</b> "
        f"{escapar(obtener_riesgo(riesgo))}",
    ]

    if interpretacion:
        partes.extend([
            "",
            "💭 <b>Posible interpretación:</b>",
            escapar(interpretacion),
        ])

    if sugerencia:
        partes.extend([
            "",
            "✨ <b>Respuesta sugerida:</b>",
            escapar(sugerencia),
        ])

    partes.extend([
        "",
        "<i>Este análisis es orientativo y "
        "puede cambiar según el contexto.</i>",
    ])

    return "\n".join(partes)


# ============================================================
# FORMATO HABLADO DEL ANÁLISIS
# ============================================================

def explicar_analisis_voz(
    texto,
    emocion,
    toxicidad,
    ghosting,
    riesgo,
    intencion,
    confianza,
):
    """
    Genera una explicación natural para Cartesia.

    No incluye etiquetas HTML ni Markdown,
    porque el contenido será convertido a voz.
    """

    nombre_emocion = obtener_nombre_emocion(emocion)
    nombre_intencion = obtener_nombre_intencion(intencion)

    configuracion = obtener_configuracion_intencion(
        intencion
    )

    introduccion = configuracion.get(
        "introduccion",
        "El mensaje puede interpretarse de varias maneras.",
    )

    interpretacion = elegir_texto(
        configuracion.get("interpretaciones", [])
    )

    sugerencia = elegir_texto(
        configuracion.get("sugerencias", [])
    )

    partes = [
        "Claro, voy a analizar el mensaje.",
        introduccion,
        f"La emoción detectada es {nombre_emocion}.",
        f"La intención parece ser: {nombre_intencion}.",
        "Recuerda que estos resultados son "
        "estimaciones y no certezas.",
    ]

    if interpretacion:
        partes.append(interpretacion)

    if sugerencia:
        partes.append(
            "Una posible respuesta sería: "
            + sugerencia
        )

    partes.append(
        "Espero que este análisis te ayude "
        "a comprender mejor el mensaje."
    )

    resultado = " ".join(partes)

    return re.sub(r"\s+", " ", resultado).strip()
