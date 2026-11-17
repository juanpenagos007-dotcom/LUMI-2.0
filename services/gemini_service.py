# ============================================================
# LUMI 💜
# SERVICIO DE INTELIGENCIA ARTIFICIAL - GEMINI
# ============================================================

import asyncio
import logging

from services.conversacion import conversar, analizar_imagen


logger = logging.getLogger("Lumi.gemini")


# ============================================================
# CONVERSACIÓN CON GEMINI
# ============================================================

async def generar_respuesta(texto):
    """
    Envía una consulta a Gemini y devuelve su respuesta.

    Utiliza la función conversar() existente,
    sin modificar conversacion.py.
    """

    texto = str(texto or "").strip()

    if not texto:
        return (
            "💜 Cuéntame qué necesitas y "
            "con gusto te ayudaré."
        )

    try:
        respuesta = await asyncio.to_thread(
            conversar,
            texto,
        )

        if respuesta is None:
            raise ValueError(
                "Gemini devolvió una respuesta vacía."
            )

        respuesta = str(respuesta).strip()

        if not respuesta:
            raise ValueError(
                "Gemini no generó contenido."
            )

        return respuesta

    except Exception:
        logger.exception(
            "Error al generar una respuesta con Gemini."
        )

        return (
            "💜 Tuve un inconveniente al procesar "
            "tu pregunta. ¿Puedes intentarlo de nuevo?"
        )


# ============================================================
# ANÁLISIS DE IMÁGENES CON GEMINI
# ============================================================

async def generar_analisis_imagen(
    imagen_bytes,
    pregunta=None,
):
    """
    Analiza una imagen utilizando Gemini.

    Parámetros:
        imagen_bytes:
            Contenido binario de la imagen.

        pregunta:
            Instrucción opcional del usuario.
    """

    if not imagen_bytes:
        return (
            "💜 No recibí una imagen válida "
            "para analizar."
        )

    pregunta = str(pregunta or "").strip()

    if not pregunta:
        pregunta = (
            "Lumi, ¿qué observas en esta imagen? "
            "Describe sus elementos principales."
        )

    try:
        respuesta = await asyncio.to_thread(
            analizar_imagen,
            imagen_bytes,
            pregunta,
        )

        if respuesta is None:
            raise ValueError(
                "Gemini no devolvió un análisis."
            )

        respuesta = str(respuesta).strip()

        if not respuesta:
            raise ValueError(
                "El análisis de la imagen está vacío."
            )

        return respuesta

    except Exception:
        logger.exception(
            "Error al analizar una imagen con Gemini."
        )

        return (
            "💜 No pude analizar esa imagen "
            "en este momento. Inténtalo nuevamente."
        )
