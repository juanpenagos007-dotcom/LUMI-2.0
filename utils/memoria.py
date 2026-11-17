# ============================================================
# LUMI 💜
# MEMORIA TEMPORAL DE LA ÚLTIMA RESPUESTA
# ============================================================

import logging

from utils.texto import enviar_texto_largo


logger = logging.getLogger("Lumi.memoria")


# ============================================================
# CONFIGURACIÓN
# ============================================================

CLAVE_ULTIMA_RESPUESTA = "ultima_respuesta"

MENSAJE_SIN_RESPUESTA = (
    "💜 Todavía no tengo una respuesta anterior "
    "para repetirte. ¡Pregúntame algo primero!"
)

MENSAJE_ERROR_AUDIO = (
    "💜 No pude convertir mi respuesta anterior "
    "en audio. Te la enviaré por escrito."
)


# ============================================================
# GUARDAR LA ÚLTIMA RESPUESTA
# ============================================================

def guardar_respuesta(context, texto):
    """
    Guarda temporalmente la última respuesta de Lumi
    en el contexto del chat de Telegram.

    No guarda la respuesta en una base de datos.
    """

    if context is None:
        return False

    if texto is None:
        return False

    respuesta = str(texto).strip()

    if not respuesta:
        return False

    context.chat_data[CLAVE_ULTIMA_RESPUESTA] = respuesta

    return True


# ============================================================
# CONSULTAR LA ÚLTIMA RESPUESTA
# ============================================================

def obtener_ultima_respuesta(context):
    """
    Recupera la última respuesta guardada.

    Devuelve:
        str  -> Respuesta disponible.
        None -> No existe una respuesta anterior.
    """

    if context is None:
        return None

    respuesta = context.chat_data.get(
        CLAVE_ULTIMA_RESPUESTA
    )

    if not respuesta:
        return None

    return str(respuesta)


# ============================================================
# COMPROBAR SI EXISTE MEMORIA
# ============================================================

def tiene_respuesta_anterior(context):
    """
    Indica si existe una respuesta anterior disponible.
    """

    return obtener_ultima_respuesta(context) is not None


# ============================================================
# RECUPERAR LA RESPUESTA ANTERIOR
# ============================================================

async def recuperar_ultima_respuesta(
    mensaje,
    context,
    tipo="texto",
):
    """
    Recupera la última respuesta de Lumi y la envía
    por escrito o mediante audio.

    Parámetros:
        mensaje:
            Mensaje recibido desde Telegram.

        context:
            Contexto del chat de Telegram.

        tipo:
            "texto" -> Envía la respuesta escrita.
            "audio" -> Convierte la respuesta a voz.

    Devuelve:
        True  -> Se atendió la solicitud.
        False -> No se pudo completar.
    """

    respuesta = obtener_ultima_respuesta(context)

    if respuesta is None:
        await mensaje.reply_text(
            MENSAJE_SIN_RESPUESTA
        )
        return False

    if tipo == "texto":
        await enviar_texto_largo(
            mensaje,
            respuesta,
        )
        return True

    if tipo == "audio":
        # Importación local para evitar dependencias
        # circulares durante la modularización.
        from services.voz_service import generar_voz

        from pathlib import Path

        from config import (
            AUDIO_FILENAME,
            AUDIO_TITLE,
            AUDIO_PERFORMER,
            AUDIO_READ_TIMEOUT,
            AUDIO_WRITE_TIMEOUT,
            AUDIO_CONNECT_TIMEOUT,
        )

        archivo_audio = None

        try:
            # generar_voz pertenece al servicio existente
            # de Cartesia y se conserva sin modificar.
            archivo_audio = await generar_voz(
                respuesta
            )

            if not archivo_audio:
                raise RuntimeError(
                    "El servicio de voz no generó un archivo."
                )

            ruta_audio = Path(archivo_audio)

            if not ruta_audio.is_file():
                raise FileNotFoundError(
                    "No se encontró el archivo de audio."
                )

            with ruta_audio.open("rb") as audio:
                await mensaje.reply_audio(
                    audio=audio,
                    filename=AUDIO_FILENAME,
                    title=AUDIO_TITLE,
                    performer=AUDIO_PERFORMER,
                    read_timeout=AUDIO_READ_TIMEOUT,
                    write_timeout=AUDIO_WRITE_TIMEOUT,
                    connect_timeout=AUDIO_CONNECT_TIMEOUT,
                )

            return True

        except Exception:
            logger.exception(
                "Error al recuperar la respuesta en audio."
            )

            await mensaje.reply_text(
                MENSAJE_ERROR_AUDIO
            )

            await enviar_texto_largo(
                mensaje,
                respuesta,
            )

            return False

        finally:
            if archivo_audio:
                try:
                    Path(archivo_audio).unlink(
                        missing_ok=True
                    )
                except OSError:
                    logger.warning(
                        "No se pudo eliminar el audio temporal."
                    )

    logger.warning(
        "Tipo de recuperación no reconocido: %s",
        tipo,
    )

    return False
