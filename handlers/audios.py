# ============================================================
# LUMI 💜
# HANDLER DE AUDIOS DE TELEGRAM
# ============================================================

import asyncio
import logging
from io import BytesIO

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from services.audio_service import transcribir_audio

from config import (
    MAX_AUDIO_BYTES,
    MAX_DURACION_AUDIO,
)

from handlers.mensajes import (
    responder_con_gemini,
    responder_con_analisis,
    mostrar_escribiendo,
    extraer_mensaje_analisis,
)

from utils.deteccion_audio import (
    detectar_peticion_anterior,
)

from utils.memoria import (
    recuperar_ultima_respuesta,
)


logger = logging.getLogger("Lumi.audios")


# ============================================================
# MENSAJES DEL SISTEMA
# ============================================================

ERROR_AUDIO = (
    "💜 No pude procesar tu audio esta vez. "
    "Intenta enviarlo nuevamente."
)

ERROR_TRANSCRIPCION = (
    "💜 No pude comprender lo que dijiste. "
    "¿Puedes intentarlo otra vez?"
)

AUDIO_DEMASIADO_GRANDE = (
    "🎙️ El archivo de audio es demasiado grande. "
    "Por favor, envía uno de máximo 10 MB."
)

AUDIO_DEMASIADO_LARGO = (
    "🎙️ El audio supera los 2 minutos permitidos. "
    "Por favor, envía uno más corto."
)


# ============================================================
# IDENTIFICAR AUDIO RECIBIDO
# ============================================================

def obtener_audio_telegram(mensaje):
    """
    Obtiene una nota de voz o un archivo de audio.
    """

    if mensaje.voice:
        return mensaje.voice

    if mensaje.audio:
        return mensaje.audio

    return None


# ============================================================
# TRANSCRIPCIÓN CON WHISPER
# ============================================================

async def transcribir_mensaje_audio(audio_bytes):
    """
    Envía los bytes del audio a Whisper.

    audio_service.transcribir_audio() es síncrona,
    por eso se ejecuta en un hilo separado.
    """

    if not audio_bytes:
        return ""

    resultado = await asyncio.to_thread(
        transcribir_audio,
        audio_bytes,
    )

    if resultado is None:
        return ""

    return str(resultado).strip()


# ============================================================
# HANDLER PRINCIPAL
# ============================================================

async def recibir_audio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Recibe una nota de voz o audio de Telegram.

    Flujo:
        1. Validar tamaño y duración.
        2. Descargar bytes del audio.
        3. Transcribir con Whisper.
        4. Interpretar la solicitud.
        5. Responder mediante voz.
    """

    mensaje = update.effective_message

    if mensaje is None:
        return

    audio = obtener_audio_telegram(mensaje)

    if audio is None:
        return

    # --------------------------------------------------------
    # 1. VALIDACIONES
    # --------------------------------------------------------

    tamano = getattr(audio, "file_size", None)
    duracion = getattr(audio, "duration", None)

    if (
        tamano is not None
        and tamano > MAX_AUDIO_BYTES
    ):
        await mensaje.reply_text(
            AUDIO_DEMASIADO_GRANDE
        )
        return

    if (
        duracion is not None
        and duracion > MAX_DURACION_AUDIO
    ):
        await mensaje.reply_text(
            AUDIO_DEMASIADO_LARGO
        )
        return

    try:
        # ----------------------------------------------------
        # 2. DESCARGAR AUDIO EN MEMORIA
        # ----------------------------------------------------

        await mostrar_escribiendo(
            update,
            context,
            ChatAction.TYPING,
        )

        archivo_telegram = await audio.get_file()

        buffer = BytesIO()

        await archivo_telegram.download_to_memory(
            out=buffer
        )

        audio_bytes = buffer.getvalue()
        buffer.close()

        if not audio_bytes:
            raise ValueError(
                "Telegram devolvió un audio vacío."
            )

        if len(audio_bytes) > MAX_AUDIO_BYTES:
            await mensaje.reply_text(
                AUDIO_DEMASIADO_GRANDE
            )
            return

        # ----------------------------------------------------
        # 3. TRANSCRIBIR CON WHISPER
        # ----------------------------------------------------

        texto = await transcribir_mensaje_audio(
            audio_bytes
        )

        if not texto:
            await mensaje.reply_text(
                ERROR_TRANSCRIPCION
            )
            return

        logger.info(
            "Audio transcrito correctamente: %r",
            texto,
        )

        # ----------------------------------------------------
        # 4. RECUPERAR RESPUESTA ANTERIOR
        # ----------------------------------------------------

        tipo_anterior = detectar_peticion_anterior(
            texto
        )

        if tipo_anterior is not None:
            await recuperar_ultima_respuesta(
                mensaje,
                context,
                tipo=tipo_anterior,
            )
            return

        # ----------------------------------------------------
        # 5. SOLICITUDES DE ANÁLISIS
        # ----------------------------------------------------

        texto_analisis = extraer_mensaje_analisis(
            texto
        )

        if texto_analisis is not None:

            if not texto_analisis:
                await mensaje.reply_text(
                    "💜 Dime qué mensaje quieres analizar."
                )
                return

            await responder_con_analisis(
                update,
                context,
                texto_analisis,
                por_voz=True,
            )
            return

        # ----------------------------------------------------
        # 6. RESPONDER HABLANDO CON GEMINI
        # ----------------------------------------------------

        await responder_con_gemini(
            update,
            context,
            texto,
            por_voz=True,
        )

    except Exception:
        logger.exception(
            "Error al procesar el audio recibido."
        )

        await mensaje.reply_text(
            ERROR_AUDIO
        )
