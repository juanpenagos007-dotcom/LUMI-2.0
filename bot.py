# ============================================================
# LUMI 💜
# Lenguaje, Unión, Memoria e Inteligencia
# Una luz para cada pregunta
# ============================================================

import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_TOKEN

from handlers.comandos import (
    bienvenida,
    ayuda,
)

from handlers.mensajes import responder
from handlers.audios import recibir_audio
from handlers.imagenes import recibir_imagen


# ============================================================
# CONFIGURACIÓN DE LOGS
# ============================================================

logging.basicConfig(
    format=(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    ),
    level=logging.INFO,
)

logger = logging.getLogger("Lumi")


# ============================================================
# MANEJO GLOBAL DE ERRORES
# ============================================================

async def manejar_error(update, context):
    """
    Registra errores inesperados de Telegram.
    """

    logger.error(
        "Error inesperado en Lumi.",
        exc_info=(
            type(context.error),
            context.error,
            context.error.__traceback__,
        ) if context.error else None,
    )

    if update and hasattr(update, "effective_message"):
        mensaje = update.effective_message

        if mensaje:
            try:
                await mensaje.reply_text(
                    "💜 Ocurrió un problema inesperado. "
                    "Inténtalo nuevamente."
                )
            except Exception:
                logger.exception(
                    "No se pudo notificar el error."
                )


# ============================================================
# INICIALIZACIÓN DEL BOT
# ============================================================

def main():
    """
    Inicializa Lumi y registra los handlers.
    """

    if not TELEGRAM_TOKEN:
        raise RuntimeError(
            "No se encontró TELEGRAM_TOKEN "
            "en el archivo .env."
        )

    logger.info("Iniciando Lumi...")

    aplicacion = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    # --------------------------------------------------------
    # COMANDOS
    # --------------------------------------------------------

    aplicacion.add_handler(
        CommandHandler(
            "start",
            bienvenida,
        )
    )

    aplicacion.add_handler(
        CommandHandler(
            "ayuda",
            ayuda,
        )
    )

    # --------------------------------------------------------
    # IMÁGENES
    # --------------------------------------------------------

    aplicacion.add_handler(
        MessageHandler(
            filters.PHOTO,
            recibir_imagen,
        )
    )

    # --------------------------------------------------------
    # AUDIOS
    # --------------------------------------------------------

    aplicacion.add_handler(
        MessageHandler(
            filters.VOICE | filters.AUDIO,
            recibir_audio,
        )
    )

    # --------------------------------------------------------
    # MENSAJES ESCRITOS
    # --------------------------------------------------------

    aplicacion.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            responder,
        )
    )

    # --------------------------------------------------------
    # ERRORES
    # --------------------------------------------------------

    aplicacion.add_error_handler(
        manejar_error
    )

    logger.info(
        "Lumi está lista para recibir mensajes."
    )

    aplicacion.run_polling(
        drop_pending_updates=False,
    )


# ============================================================
# PUNTO DE ENTRADA
# ============================================================

if __name__ == "__main__":
    main()
