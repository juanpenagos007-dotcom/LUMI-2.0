import logging
import os
import tempfile

from faster_whisper import WhisperModel

logger = logging.getLogger("Lumi.Audio")

# Modelo ligero para ejecutar en CPU.
MODELO_AUDIO = "base"

# Se carga una sola vez, cuando llegue el primer audio.
modelo = None


def obtener_modelo():
    global modelo

    if modelo is None:
        logger.info(
            "Cargando modelo de reconocimiento de voz..."
        )

        modelo = WhisperModel(
            MODELO_AUDIO,
            device="cpu",
            compute_type="int8",
        )

        logger.info(
            "Modelo de reconocimiento de voz listo."
        )

    return modelo


def transcribir_audio(audio_bytes):
    """
    Convierte una nota de voz de Telegram en texto.

    Recibe los bytes del audio OGG/Opus.
    Devuelve el texto reconocido.
    """
    if not audio_bytes:
        return ""

    ruta_temporal = None

    try:
        # Crear un archivo temporal para Whisper.
        with tempfile.NamedTemporaryFile(
            suffix=".ogg",
            delete=False,
        ) as archivo:
            archivo.write(audio_bytes)
            ruta_temporal = archivo.name

        whisper = obtener_modelo()

        segmentos, informacion = whisper.transcribe(
            ruta_temporal,
            beam_size=3,
            vad_filter=True,
            language=None,
        )

        texto = " ".join(
            segmento.text.strip()
            for segmento in segmentos
            if segmento.text.strip()
        ).strip()

        logger.info(
            "Audio transcrito. Idioma detectado: %s",
            informacion.language,
        )

        return texto

    except Exception:
        logger.exception(
            "Error durante la transcripción del audio."
        )
        raise

    finally:
        # Eliminar el archivo temporal.
        if ruta_temporal and os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)
