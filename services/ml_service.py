# ============================================================
# LUMI 💜
# SERVICIO DE MACHINE LEARNING
# ============================================================

import asyncio
import logging

from predict import analizar_texto


logger = logging.getLogger("Lumi.ml")


# ============================================================
# ANALIZAR MENSAJES
# ============================================================

async def analizar_mensaje(texto):
    """
    Ejecuta el modelo de Machine Learning existente.

    Retorna seis valores:
        emocion
        toxicidad
        ghosting
        riesgo
        intencion
        confianza

    No modifica predict.py.
    """

    texto = str(texto or "").strip()

    if not texto:
        raise ValueError(
            "No se puede analizar un mensaje vacío."
        )

    try:
        resultado = await asyncio.to_thread(
            analizar_texto,
            texto,
        )

        if not isinstance(resultado, (tuple, list)):
            raise TypeError(
                "El modelo debe devolver una tupla "
                "o lista con seis resultados."
            )

        if len(resultado) != 6:
            raise ValueError(
                "El modelo devolvió "
                f"{len(resultado)} valores; "
                "se esperaban seis."
            )

        (
            emocion,
            toxicidad,
            ghosting,
            riesgo,
            intencion,
            confianza,
        ) = resultado

        return (
            emocion,
            toxicidad,
            ghosting,
            riesgo,
            intencion,
            confianza,
        )

    except Exception:
        logger.exception(
            "Error al analizar el mensaje con ML."
        )
        raise
