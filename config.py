import os
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# LUMI 💜
# CONFIGURACIÓN GENERAL
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

# Cargar las variables del archivo .env
load_dotenv(
    BASE_DIR / ".env",
    override=True,
)


# ============================================================
# TELEGRAM
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# ============================================================
# LÍMITES DEL BOT
# ============================================================

MAX_MENSAJE = 3900

MAX_ANALISIS = 2500

MAX_IMAGEN_BYTES = 10 * 1024 * 1024

MAX_AUDIO_BYTES = 10 * 1024 * 1024

MAX_DURACION_AUDIO = 120


# ============================================================
# IDENTIDAD DE LUMI
# ============================================================

BOT_NOMBRE = "Lumi"

BOT_NOMBRE_COMPLETO = "L.U.M.I."

BOT_SIGNIFICADO = (
    "Lenguaje, Unión, Memoria e Inteligencia"
)

BOT_ESLOGAN = "Una luz para cada pregunta"

BOT_CREADOR = "Juan Esteban Benítez Penagos"


# ============================================================
# ARCHIVOS DE AUDIO
# ============================================================

AUDIO_FILENAME = "Lumi_AI.mp3"

AUDIO_TITLE = "Lumi"

AUDIO_PERFORMER = "Lumi AI"


# ============================================================
# TIEMPOS DE ESPERA DE TELEGRAM
# ============================================================

AUDIO_READ_TIMEOUT = 180

AUDIO_WRITE_TIMEOUT = 180

AUDIO_CONNECT_TIMEOUT = 60
