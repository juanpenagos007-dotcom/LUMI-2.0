# ============================================================
# LUMI 💜
# HANDLERS DE COMANDOS DE TELEGRAM
# ============================================================

import logging
from html import escape

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import (
    BOT_NOMBRE,
    BOT_NOMBRE_COMPLETO,
    BOT_SIGNIFICADO,
    BOT_ESLOGAN,
)


logger = logging.getLogger("Lumi.comandos")


# ============================================================
# UTILIDADES
# ============================================================

async def enviar_mensaje_comando(mensaje, texto, respaldo):
    """
    Envía un mensaje con formato HTML.

    Si Telegram rechaza el formato, intenta enviar
    una versión sencilla como respaldo.
    """

    try:
        await mensaje.reply_text(
            texto,
            parse_mode=ParseMode.HTML,
        )

    except Exception:
        logger.exception(
            "Error al enviar un mensaje de comando."
        )

        try:
            await mensaje.reply_text(respaldo)

        except Exception:
            logger.exception(
                "No fue posible enviar el mensaje de respaldo."
            )


# ============================================================
# COMANDO /START
# ============================================================

async def bienvenida(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Presenta Lumi y sus capacidades principales
    al iniciar la conversación.
    """

    mensaje = update.effective_message

    if mensaje is None:
        return

    usuario = update.effective_user

    nombre = (
        usuario.first_name
        if usuario and usuario.first_name
        else "amigo"
    )

    nombre = escape(nombre)

    bot_nombre = escape(str(BOT_NOMBRE))
    bot_nombre_completo = escape(str(BOT_NOMBRE_COMPLETO))
    bot_significado = escape(str(BOT_SIGNIFICADO))
    bot_eslogan = escape(str(BOT_ESLOGAN))

    texto = (
        f"💜 <b>¡Hola, {nombre}!</b>\n\n"

        f"Soy <b>{bot_nombre}</b>, tu asistente "
        "de inteligencia artificial.\n\n"

        f"✨ <b>{bot_nombre_completo}</b>\n"
        f"{bot_significado}\n\n"

        f"🌟 <i>{bot_eslogan}</i>\n\n"

        "Estoy aquí para ayudarte a aprender, "
        "resolver dudas y descubrir cosas nuevas.\n\n"

        "✨ <b>¿Qué puedo hacer por ti?</b>\n\n"

        "🤖 <b>Conversar contigo:</b> responder "
        "preguntas y explicar temas.\n\n"

        "🧠 <b>Analizar mensajes:</b> identificar "
        "emociones y características del texto "
        "de manera orientativa.\n\n"

        "🎙️ <b>Escuchar y hablar:</b> comprender "
        "mensajes de voz y generar respuestas "
        "habladas.\n\n"

        "🖼️ <b>Analizar fotografías:</b> describir "
        "imágenes y responder preguntas sobre ellas.\n\n"

        "🌐 <b>Buscar información:</b> consultar "
        "internet cuando necesites datos actuales.\n\n"

        "🎵 <b>Buscar música:</b> encontrar canciones "
        "y compartir enlaces para escucharlas "
        "en YouTube.\n\n"

        "🔁 <b>Recordar mi última respuesta:</b> "
        "puedes pedirme que la repita.\n\n"

        "💡 <b>¿Cómo empezamos?</b>\n"
        "Solo escríbeme normalmente, envíame "
        "una fotografía o un mensaje de voz.\n\n"

        "📖 Escribe /ayuda para descubrir "
        "cómo utilizar mis funciones.\n\n"

        "💜 <b>¿En qué puedo ayudarte hoy?</b>"
    )

    respaldo = (
        f"💜 ¡Hola! Soy {BOT_NOMBRE}.\n\n"
        "Puedo conversar contigo, analizar mensajes "
        "e imágenes, comprender audios, responder "
        "con voz, buscar información y encontrar "
        "música en YouTube.\n\n"
        "Escribe /ayuda para conocer mis funciones."
    )

    await enviar_mensaje_comando(
        mensaje,
        texto,
        respaldo,
    )


# ============================================================
# COMANDO /AYUDA
# ============================================================

async def ayuda(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Muestra las funciones y ejemplos de uso
    disponibles en Lumi 2.0.
    """

    mensaje = update.effective_message

    if mensaje is None:
        return

    texto = (
        "💜 <b>CENTRO DE AYUDA DE LUMI 2.0</b>\n\n"

        "¡Hola! Aquí encontrarás las funciones "
        "que puedes utilizar conmigo.\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"

        "🤖 <b>1. CONVERSACIÓN INTELIGENTE</b>\n\n"

        "Puedes preguntarme sobre programación, "
        "tecnología, estudios, cultura general "
        "y muchos otros temas.\n\n"

        "<b>Ejemplos:</b>\n"
        "• Lumi, ¿qué es Python?\n"
        "• Explícame qué es una API REST.\n"
        "• ¿Cuál es la diferencia entre "
        "React y Angular?\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"

        "🎙️ <b>2. RESPUESTAS CON VOZ</b>\n\n"

        "Puedes pedirme que responda mediante "
        "un mensaje de audio.\n\n"

        "<b>Ejemplos:</b>\n"
        "• Lumi, explícame en audio qué es React.\n"
        "• Mándame un audio sobre JavaScript.\n"
        "• Respóndeme con tu voz.\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"

        "🎧 <b>3. MENSAJES DE VOZ</b>\n\n"

        "Envíame un mensaje de voz desde Telegram. "
        "Podré transcribirlo, comprender tu pregunta "
        "y responderte.\n\n"

        "<b>Ejemplo:</b>\n"
        "🎤 Envía una nota de voz preguntando "
        "qué es la inteligencia artificial.\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"

        "🖼️ <b>4. ANÁLISIS DE IMÁGENES</b>\n\n"

        "Puedes enviarme una fotografía y "
        "preguntarme qué aparece en ella.\n\n"

        "<b>Ejemplos:</b>\n"
        "• Envía una fotografía sin descripción "
        "para que la analice.\n"
        "• Adjunta una fotografía y escribe: "
        "¿Qué objetos aparecen aquí?\n"
        "• ¿Qué puedes observar en esta imagen?\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"

        "🧠 <b>5. ANÁLISIS DE MENSAJES</b>\n\n"

        "Puedo realizar un análisis orientativo "
        "de emociones, intenciones y características "
        "de un texto mediante Machine Learning.\n\n"

        "<b>Ejemplo:</b>\n"
        "<i>Analiza este mensaje: "
        "Muchas gracias por ayudarme.</i>\n\n"

        "Los resultados son orientativos "
        "y no constituyen un diagnóstico.\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"

        "🌐 <b>6. BÚSQUEDAS EN INTERNET</b>\n\n"

        "Cuando necesitas información reciente, "
        "puedo consultar fuentes disponibles "
        "en internet y ayudarte a comprenderlas.\n\n"

        "<b>Ejemplos:</b>\n"
        "• Lumi, busca información sobre Python.\n"
        "• Investiga las últimas novedades "
        "de inteligencia artificial.\n"
        "• ¿Cuáles son las noticias recientes "
        "sobre tecnología?\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"

        "🎵 <b>7. BÚSQUEDA DE MÚSICA</b>\n\n"

        "Puedes pedirme una canción por su título "
        "o por el nombre de su artista.\n\n"

        "Buscaré información de la canción "
        "y compartiré enlaces disponibles "
        "para escucharla en YouTube.\n\n"

        "<b>Ejemplos:</b>\n"
        "• Lumi, ponme Billie Jean "
        "de Michael Jackson.\n"
        "• Quiero escuchar Take On Me de a-ha.\n"
        "• Lumi, sorpréndeme con una canción.\n\n"

        "La reproducción se realiza mediante "
        "los enlaces compartidos.\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"

        "🔁 <b>8. REPETIR RESPUESTAS</b>\n\n"

        "Puedes pedirme que repita "
        "mi última respuesta disponible.\n\n"

        "<b>Ejemplos:</b>\n"
        "• Lumi, repíteme lo último.\n"
        "• Léeme eso en audio.\n"
        "• Escríbeme tu respuesta anterior.\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"

        "📌 <b>COMANDOS DISPONIBLES</b>\n\n"

        "/start — Mostrar la bienvenida.\n"
        "/ayuda — Mostrar este centro de ayuda.\n\n"

        "💡 <b>RECUERDA</b>\n\n"

        "No necesitas escribir un comando "
        "para conversar conmigo. Puedes hablarme "
        "de forma natural.\n\n"

        "Algunas funciones dependen de servicios "
        "externos y pueden tener límites "
        "temporales de disponibilidad.\n\n"

        "💜 <i>Una luz para cada pregunta.</i>"
    )

    respaldo = (
        "💜 AYUDA DE LUMI 2.0\n\n"

        "Puedes utilizar estas funciones:\n\n"

        "🤖 Conversación inteligente.\n"
        "🎙️ Respuestas mediante voz.\n"
        "🎧 Comprensión de mensajes de voz.\n"
        "🖼️ Análisis de fotografías.\n"
        "🧠 Análisis orientativo de mensajes.\n"
        "🌐 Búsquedas en internet.\n"
        "🎵 Búsqueda de música en YouTube.\n"
        "🔁 Repetición de respuestas.\n\n"

        "Comandos:\n"
        "/start - Bienvenida.\n"
        "/ayuda - Centro de ayuda.\n\n"

        "💜 Puedes escribirme normalmente."
    )

    await enviar_mensaje_comando(
        mensaje,
        texto,
        respaldo,
    )
