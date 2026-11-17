# ============================================================
# LUMI 💜
# HANDLER DE IMÁGENES DE TELEGRAM
# ============================================================

import logging
from io import BytesIO

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from config import MAX_IMAGEN_BYTES

from services.gemini_service import (
    generar_analisis_imagen,
)

from utils.memoria import guardar_respuesta

from utils.texto import enviar_texto_largo


logger = logging.getLogger("Lumi.imagenes")


# ============================================================
# MENSAJES DEL SISTEMA
# ============================================================

ERROR_IMAGEN = (
    "💜 No pude analizar esa imagen en este "
    "momento. Inténtalo nuevamente."
)

IMAGEN_DEMASIADO_GRANDE = (
    "🖼️ La imagen supera el límite de 10 MB. "
    "Por favor, envía una más pequeña."
)

PREGUNTA_PREDETERMINADA = (
    "¿Qué observas en esta fotografía? "
    "Describe sus elementos principales."
)


# ============================================================
# OBTENER FOTOGRAFÍA
# ============================================================

def obtener_fotografia(mensaje):
    """
    Selecciona la fotografía de mayor resolución
    disponible en el mensaje de Telegram.

    Devuelve None si el mensaje no contiene fotos.
    """

    if not mensaje or not mensaje.photo:
        return None

    return mensaje.photo[-1]


# ============================================================
# DESCARGAR IMAGEN EN MEMORIA
# ============================================================

async def descargar_imagen(fotografia):
    """
    Descarga una imagen de Telegram directamente
    en memoria y devuelve sus bytes.
    """

    archivo = await fotografia.get_file()

    buffer = BytesIO()

    await archivo.download_to_memory(
        out=buffer
    )

    imagen_bytes = buffer.getvalue()

    buffer.close()

    return imagen_bytes


# ============================================================
# HANDLER PRINCIPAL DE IMÁGENES
# ============================================================

async def recibir_imagen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Recibe una fotografía y solicita su análisis
    a Gemini.

    Flujo:
        1. Obtener fotografía.
        2. Validar tamaño.
        3. Descargar imagen.
        4. Obtener pregunta del usuario.
        5. Analizar mediante Gemini.
        6. Enviar y guardar la respuesta.
    """

    mensaje = update.effective_message

    if mensaje is None:
        return

    fotografia = obtener_fotografia(
        mensaje
    )

    if fotografia is None:
        return

    # --------------------------------------------------------
    # 1. COMPROBAR TAMAÑO
    # --------------------------------------------------------

    tamano = getattr(
        fotografia,
        "file_size",
        None,
    )

    if (
        tamano is not None
        and tamano > MAX_IMAGEN_BYTES
    ):
        await mensaje.reply_text(
            IMAGEN_DEMASIADO_GRANDE
        )
        return

    try:
        # ----------------------------------------------------
        # 2. MOSTRAR ACTIVIDAD
        # ----------------------------------------------------

        if update.effective_chat:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.TYPING,
            )

        # ----------------------------------------------------
        # 3. DESCARGAR IMAGEN
        # ----------------------------------------------------

        imagen_bytes = await descargar_imagen(
            fotografia
        )

        if not imagen_bytes:
            raise ValueError(
                "Telegram devolvió una imagen vacía."
            )

        if len(imagen_bytes) > MAX_IMAGEN_BYTES:
            await mensaje.reply_text(
                IMAGEN_DEMASIADO_GRANDE
            )
            return

        # ----------------------------------------------------
        # 4. OBTENER PREGUNTA
        # ----------------------------------------------------

        pregunta = (
            mensaje.caption or ""
        ).strip()

        if not pregunta:
            pregunta = PREGUNTA_PREDETERMINADA

        # ----------------------------------------------------
        # 5. CONSULTAR GEMINI
        # ----------------------------------------------------

        respuesta = await generar_analisis_imagen(
            imagen_bytes,
            pregunta,
        )

        if not respuesta:
            raise ValueError(
                "Gemini devolvió una respuesta vacía."
            )

        # ----------------------------------------------------
        # 6. GUARDAR RESPUESTA
        # ----------------------------------------------------

        guardar_respuesta(
            context,
            respuesta,
        )

        # ----------------------------------------------------
        # 7. ENVIAR RESPUESTA
        # ----------------------------------------------------

        await enviar_texto_largo(
            mensaje,
            respuesta,
        )

        logger.info(
            "Imagen analizada correctamente en el chat %s.",
            update.effective_chat.id
            if update.effective_chat
            else "desconocido",
        )

    except Exception:
        logger.exception(
            "Error al procesar la imagen recibida."
        )

        await mensaje.reply_text(
            ERROR_IMAGEN
        )
