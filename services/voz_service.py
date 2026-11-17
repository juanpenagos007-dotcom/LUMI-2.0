
import os
import re
import io
import wave
import asyncio
import tempfile
import logging
import subprocess
import shutil
from pathlib import Path

from dotenv import load_dotenv
from cartesia import Cartesia


# ============================================================
# CONFIGURACIÓN DE Lumi 💜
# ============================================================

logger = logging.getLogger("Lumi.Voz")

CARPETA_PROYECTO = Path(__file__).resolve().parent.parent
load_dotenv(CARPETA_PROYECTO / ".env")

API_KEY = os.getenv("CARTESIA_API_KEY")
VOICE_ID = os.getenv("CARTESIA_VOICE_ID")

MODELO = "sonic-3"
IDIOMA = "es"

VELOCIDAD = 0.85
MAX_CARACTERES = 1800

SAMPLE_RATE = 44100
BITRATE_MP3 = "64k"


# ============================================================
# LIMPIEZA DEL TEXTO
# ============================================================

def limpiar_texto_voz(texto):
    if not texto:
        return ""

    texto = str(texto)

    texto = re.sub(
        r"```[\s\S]*?```",
        " ",
        texto,
    )

    texto = re.sub(r"<[^>]+>", "", texto)

    texto = re.sub(
        r"\[([^\]]+)\]\([^)]+\)",
        r"\1",
        texto,
    )

    texto = re.sub(r"https?://\S+", "", texto)
    texto = re.sub(r"[*_`#~]", "", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


# ============================================================
# DIVISIÓN DE RESPUESTAS LARGAS
# ============================================================

def dividir_texto_voz(texto):
    if len(texto) <= MAX_CARACTERES:
        return [texto]

    oraciones = re.split(
        r"(?<=[.!?])\s+",
        texto,
    )

    fragmentos = []
    actual = ""

    for oracion in oraciones:
        oracion = oracion.strip()

        if not oracion:
            continue

        palabras = oracion.split()
        partes = []
        parte = ""

        for palabra in palabras:
            candidato = f"{parte} {palabra}".strip()

            if len(candidato) > MAX_CARACTERES and parte:
                partes.append(parte)
                parte = palabra
            else:
                parte = candidato

        if parte:
            partes.append(parte)

        for segmento in partes:
            candidato = f"{actual} {segmento}".strip()

            if len(candidato) <= MAX_CARACTERES:
                actual = candidato
            else:
                if actual:
                    fragmentos.append(actual)
                actual = segmento

    if actual:
        fragmentos.append(actual)

    return fragmentos


# ============================================================
# CONVERSIÓN A MP3
# ============================================================

def convertir_a_mp3(ruta_wav):
    ffmpeg = shutil.which("ffmpeg")

    if not ffmpeg:
        raise RuntimeError(
            "FFmpeg no está instalado o no está "
            "disponible en el PATH de Windows."
        )

    descriptor, ruta_mp3 = tempfile.mkstemp(
        prefix="lightby_",
        suffix=".mp3",
    )
    os.close(descriptor)

    try:
        comando = [
            ffmpeg,
            "-y",
            "-loglevel", "error",
            "-i", ruta_wav,
            "-vn",
            "-codec:a", "libmp3lame",
            "-b:a", BITRATE_MP3,
            ruta_mp3,
        ]

        subprocess.run(
            comando,
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )

        if os.path.getsize(ruta_mp3) == 0:
            raise RuntimeError(
                "El archivo MP3 quedó vacío."
            )

        logger.info(
            "Audio convertido a MP3: %.2f MB",
            os.path.getsize(ruta_mp3) / (1024 * 1024),
        )

        return ruta_mp3

    except Exception:
        if os.path.exists(ruta_mp3):
            os.remove(ruta_mp3)
        raise


# ============================================================
# GENERACIÓN DE VOZ CON CARTESIA
# ============================================================

def generar_voz_cartesia(texto):
    if not API_KEY or not VOICE_ID:
        raise RuntimeError(
            "Falta CARTESIA_API_KEY o CARTESIA_VOICE_ID "
            "en el archivo .env."
        )

    ruta_wav = None

    try:
        cliente = Cartesia(api_key=API_KEY)

        fragmentos = dividir_texto_voz(texto)

        logger.info(
            "Generando voz de Ximena en %s fragmento(s).",
            len(fragmentos),
        )

        descriptor, ruta_wav = tempfile.mkstemp(
            prefix="lightby_",
            suffix=".wav",
        )
        os.close(descriptor)

        with wave.open(ruta_wav, "wb") as salida:
            parametros = None

            for indice, fragmento in enumerate(
                fragmentos, start=1
            ):
                logger.info(
                    "Generando fragmento %s de %s.",
                    indice,
                    len(fragmentos),
                )

                respuesta = cliente.tts.generate(
                    model_id=MODELO,
                    transcript=fragmento,
                    voice={
                        "mode": "id",
                        "id": VOICE_ID,
                    },
                    language=IDIOMA,
                    generation_config={
                        "speed": VELOCIDAD,
                    },
                    output_format={
                        "container": "wav",
                        "encoding": "pcm_s16le",
                        "sample_rate": SAMPLE_RATE,
                    },
                )

                audio_bytes = respuesta.read()

                if not audio_bytes:
                    raise RuntimeError(
                        "Cartesia devolvió audio vacío."
                    )

                with wave.open(
                    io.BytesIO(audio_bytes), "rb"
                ) as entrada:

                    configuracion = (
                        entrada.getnchannels(),
                        entrada.getsampwidth(),
                        entrada.getframerate(),
                        entrada.getcomptype(),
                    )

                    if parametros is None:
                        parametros = configuracion

                        salida.setnchannels(
                            entrada.getnchannels()
                        )
                        salida.setsampwidth(
                            entrada.getsampwidth()
                        )
                        salida.setframerate(
                            entrada.getframerate()
                        )

                    elif configuracion != parametros:
                        raise RuntimeError(
                            "Los fragmentos tienen "
                            "formatos incompatibles."
                        )

                    datos = entrada.readframes(
                        entrada.getnframes()
                    )

                    salida.writeframes(datos)

        if os.path.getsize(ruta_wav) <= 44:
            raise RuntimeError(
                "El audio generado está vacío."
            )

        ruta_mp3 = convertir_a_mp3(ruta_wav)

        logger.info(
            "Voz MP3 de Lumi generada correctamente."
        )

        return ruta_mp3

    except Exception:
        logger.exception(
            "Error al generar la voz de Lumi."
        )
        raise

    finally:
        if ruta_wav and os.path.exists(ruta_wav):
            try:
                os.remove(ruta_wav)
            except OSError:
                logger.warning(
                    "No se pudo eliminar el WAV temporal."
                )


# ============================================================
# FUNCIÓN UTILIZADA POR BOT.PY
# ============================================================

async def generar_voz(texto):
    texto = limpiar_texto_voz(texto)

    if not texto:
        logger.warning(
            "No se recibió texto para generar voz."
        )
        return None

    return await asyncio.to_thread(
        generar_voz_cartesia,
        texto,
    )
