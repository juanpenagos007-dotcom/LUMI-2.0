
# ============================================================
# LUMI 💜 - HANDLER DE MENSAJES ESCRITOS
# Música mediante iTunes y YouTube, sin archivos locales
# ============================================================

import asyncio
import logging
import random
import re
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from config import (
    AUDIO_FILENAME,
    AUDIO_TITLE,
    AUDIO_PERFORMER,
    AUDIO_READ_TIMEOUT,
    AUDIO_WRITE_TIMEOUT,
    AUDIO_CONNECT_TIMEOUT,
)

from services.gemini_service import generar_respuesta
from services.ml_service import analizar_mensaje
from services.musica_service import buscar_cancion, formatear_cancion

from utils.deteccion_tiempo import detectar_consulta_tiempo
from utils.texto import enviar_texto_largo

from utils.deteccion_audio import (
    extraer_peticion_audio,
    detectar_peticion_anterior,
)

from utils.deteccion_musica import (
    extraer_peticion_musica,
    extraer_correccion_musica,
    construir_consulta_corregida,
    es_confirmacion_musical,
    es_cancelacion_musical,
    normalizar_musica,
)

from utils.memoria import (
    guardar_respuesta,
    recuperar_ultima_respuesta,
)

from utils.formato_analisis import (
    formatear_analisis,
    explicar_analisis_voz,
)

logger = logging.getLogger("Lumi.mensajes")


# ============================================================
# CONFIGURACIÓN MUSICAL
# ============================================================

CANCIONES_SORPRESA = (
    "Take On Me a-ha",
    "Billie Jean Michael Jackson",
    "Vivir Mi Vida Marc Anthony",
    "Bohemian Rhapsody Queen",
    "La Camisa Negra Juanes",
    "Dancing Queen ABBA",
    "Bachata en Fukuoka Juan Luis Guerra",
    "Color Esperanza Diego Torres",
)


# ============================================================
# DETECCIÓN DE SOLICITUDES DE ANÁLISIS
# ============================================================

PATRON_ANALISIS = re.compile(
    r"^\s*(?:(?:hola|oye|hey)[,!.]?\s+)?"
    r"(?:(?:lumi|l\.?\s*u\.?\s*m\.?\s*i\.?|lightby|light by)[,!.]?\s+)?"
    r"(?:(?:por favor)[,]?\s+)?"
    r"(?:analiza|anal[ií]zame|analizar|"
    r"haz un an[aá]lisis de|quiero que analices)"
    r"\s+(?:(?:este|esta|el|la|siguiente|un|una)\s+)?"
    r"(?:mensaje|texto|frase|conversaci[oó]n|respuesta)"
    r"\s*(?::|que dice|donde dice)?\s*",
    re.IGNORECASE,
)


def extraer_mensaje_analisis(texto):
    """
    Extrae el texto que el usuario desea analizar.
    """
    original = str(texto or "").strip()

    if not original:
        return None

    coincidencia = PATRON_ANALISIS.match(original)

    if coincidencia is None:
        return None

    return original[coincidencia.end():].strip()


# ============================================================
# INDICADOR DE ACTIVIDAD
# ============================================================

async def mostrar_escribiendo(
    update,
    context,
    accion=ChatAction.TYPING,
):
    chat = update.effective_chat

    if chat is None:
        return

    try:
        await context.bot.send_chat_action(
            chat_id=chat.id,
            action=accion,
        )
    except Exception:
        logger.warning(
            "No se pudo mostrar el indicador de actividad."
        )


# ============================================================
# RESPUESTAS HABLADAS - CARTESIA
# ============================================================

async def enviar_respuesta_hablada(mensaje, respuesta):
    """
    Genera y envía una respuesta hablada mediante
    el servicio de voz existente de Lumi.
    """
    from services.voz_service import generar_voz

    archivo_audio = None

    try:
        if asyncio.iscoroutinefunction(generar_voz):
            archivo_audio = await generar_voz(respuesta)
        else:
            archivo_audio = await asyncio.to_thread(
                generar_voz,
                respuesta,
            )

        if not archivo_audio:
            raise RuntimeError(
                "No se generó ningún archivo de audio."
            )

        ruta_audio = Path(archivo_audio)

        if not ruta_audio.is_file():
            raise FileNotFoundError(
                "No se encontró el archivo generado."
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
            "No se pudo enviar la respuesta hablada."
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


# ============================================================
# CONVERSACIÓN CON GEMINI
# ============================================================

async def responder_con_gemini(
    update,
    context,
    texto,
    por_voz=False,
):
    mensaje = update.effective_message

    if mensaje is None:
        return

    texto = str(texto or "").strip()

    if not texto:
        await mensaje.reply_text(
            "💜 ¿Sobre qué tema quieres que te hable?"
        )
        return

    await mostrar_escribiendo(
        update,
        context,
        (
            ChatAction.UPLOAD_VOICE
            if por_voz
            else ChatAction.TYPING
        ),
    )

    respuesta = detectar_consulta_tiempo(texto)

    if (
        respuesta is None
        and mensaje.text
        and mensaje.text != texto
    ):
        respuesta = detectar_consulta_tiempo(
            mensaje.text
        )

    if respuesta is None:
        respuesta = await generar_respuesta(texto)

    guardar_respuesta(context, respuesta)

    if por_voz:
        enviado = await enviar_respuesta_hablada(
            mensaje,
            respuesta,
        )

        if enviado:
            return

        await mensaje.reply_text(
            "💜 No pude generar el audio esta vez. "
            "Te compartiré la respuesta por escrito."
        )

    await enviar_texto_largo(
        mensaje,
        respuesta,
    )


# ============================================================
# ANÁLISIS DE MACHINE LEARNING
# ============================================================

async def responder_con_analisis(
    update,
    context,
    texto,
    por_voz=False,
):
    mensaje = update.effective_message

    if mensaje is None:
        return

    texto = str(texto or "").strip()

    if not texto:
        await mensaje.reply_text(
            "💜 Envíame el mensaje que quieres analizar."
        )
        return

    await mostrar_escribiendo(
        update,
        context,
        ChatAction.TYPING,
    )

    try:
        (
            emocion,
            toxicidad,
            ghosting,
            riesgo,
            intencion,
            confianza,
        ) = await analizar_mensaje(texto)

    except Exception:
        logger.exception(
            "No se pudo completar el análisis ML."
        )

        await mensaje.reply_text(
            "💜 No pude analizar ese mensaje "
            "en este momento. Inténtalo nuevamente."
        )
        return

    explicacion_voz = explicar_analisis_voz(
        texto,
        emocion,
        toxicidad,
        ghosting,
        riesgo,
        intencion,
        confianza,
    )

    guardar_respuesta(
        context,
        explicacion_voz,
    )

    if por_voz:
        await mostrar_escribiendo(
            update,
            context,
            ChatAction.UPLOAD_VOICE,
        )

        enviado = await enviar_respuesta_hablada(
            mensaje,
            explicacion_voz,
        )

        if enviado:
            return

        await mensaje.reply_text(
            "💜 No pude generar el audio. "
            "Te enviaré el análisis por escrito."
        )

    resultado_html = formatear_analisis(
        texto,
        emocion,
        toxicidad,
        ghosting,
        riesgo,
        intencion,
        confianza,
    )

    try:
        await mensaje.reply_text(
            resultado_html,
            parse_mode=ParseMode.HTML,
        )

    except Exception:
        logger.exception(
            "Error al enviar el análisis HTML."
        )

        await enviar_texto_largo(
            mensaje,
            explicacion_voz,
        )


# ============================================================
# MÚSICA SORPRESA
# ============================================================

def es_sorpresa_musical(texto):
    """
    Reconoce solicitudes de canciones aleatorias.
    """
    texto = normalizar_musica(texto)

    return bool(
        re.search(
            r"\b(?:"
            r"sorprendeme|"
            r"ponme algo al azar|"
            r"pon musica aleatoria|"
            r"elige (?:una )?cancion|"
            r"cualquier cancion"
            r")\b",
            texto,
        )
    )


def es_respuesta_musical_pendiente(texto):
    """
    Comprueba si el mensaje puede ser un título
    o el nombre de un artista.
    """
    limpio = normalizar_musica(texto).strip(
        " ¿?¡!.,"
    )

    if not limpio or len(limpio) > 110:
        return False

    if es_cancelacion_musical(texto):
        return False

    if "?" in texto:
        return False

    if re.match(
        r"^(?:"
        r"hola|adios|gracias|que|como|cuando|"
        r"donde|por que|analiza|explica|"
        r"investiga|busca en internet|"
        r"dime la hora|cuentame|responde|hablame"
        r")\b",
        limpio,
    ):
        return False

    return True


# ============================================================
# PREGUNTAS SOBRE LA ÚLTIMA CANCIÓN
# ============================================================

def es_pregunta_sobre_ultima_cancion(texto):
    """
    Reconoce preguntas sobre una canción anterior.
    """
    limpio = normalizar_musica(texto)

    referencia = bool(
        re.search(
            r"\b(?:"
            r"esa cancion|esta cancion|"
            r"ese tema|esa musica|"
            r"la cancion anterior|"
            r"la que me pusiste|"
            r"ese artista"
            r")\b",
            limpio,
        )
    )

    pregunta = bool(
        re.search(
            r"\b(?:"
            r"que|cuando|quien|cual|como|"
            r"por que|cuentame|explicame|"
            r"investiga|informacion|historia"
            r")\b",
            limpio,
        )
    )

    return referencia and pregunta


# ============================================================
# ENVÍO DE RESULTADOS MUSICALES
# ============================================================

async def enviar_resultado_musical(
    mensaje,
    cancion,
    sorpresa=False,
):
    """
    Envía la canción y sus enlaces.

    Los videos directos se envían por separado
    para permitir la vista previa de Telegram.
    """
    respuesta = formatear_cancion(cancion)

    if sorpresa:
        respuesta = (
            "🎲 ¡Aquí tienes una sorpresa musical! 💜\n\n"
            + respuesta
        )

    enlace = cancion.get("enlace_youtube")

    youtube_directo = bool(
        cancion.get("youtube_directo")
        and enlace
    )

    if not youtube_directo:
        await enviar_texto_largo(
            mensaje,
            respuesta,
        )
        return respuesta

    titulo = (
        cancion.get("titulo")
        or "Canción encontrada"
    )

    artista = (
        cancion.get("artista")
        or "Artista desconocido"
    )

    encabezado = (
        "🎲 ¡Sorpresa musical! 💜\n\n"
        if sorpresa
        else "🎶💜 ¡Encontré esta canción!\n\n"
    )

    encabezado += (
        f"🎵 {titulo}\n"
        f"🎤 {artista}"
    )

    await mensaje.reply_text(encabezado)

    await mensaje.reply_text(
        enlace,
        disable_web_page_preview=False,
    )

    plataformas = []

    enlace_spotify = cancion.get(
        "enlace_spotify"
    )

    enlace_apple = cancion.get(
        "enlace_apple"
    )

    if enlace_spotify:
        plataformas.append(
            f"🟢 Spotify: {enlace_spotify}"
        )

    if enlace_apple:
        plataformas.append(
            f"🍎 Apple Music: {enlace_apple}"
        )

    if plataformas:
        await mensaje.reply_text(
            "🎧 Otras plataformas:\n"
            + "\n".join(plataformas),
            disable_web_page_preview=True,
        )

    return respuesta


# ============================================================
# BÚSQUEDA MUSICAL
# ============================================================

async def responder_con_musica(
    update,
    context,
    consulta,
    sorpresa=False,
):
    """
    Busca canciones utilizando musica_service.py.

    Mantiene el título y artista encontrados
    para poder corregir búsquedas posteriores.
    """
    mensaje = update.effective_message

    if mensaje is None:
        return

    if sorpresa:
        consulta = random.choice(
            CANCIONES_SORPRESA
        )
    else:
        consulta = str(
            consulta or ""
        ).strip()

    if not consulta:
        context.user_data[
            "lumi_esperando_musica"
        ] = True

        respuesta = (
            "🎶💜 ¡Claro! ¿Qué canción, artista "
            "o género quieres escuchar? "
            "También puedes decirme «sorpréndeme» "
            "y elijo una para ti."
        )

        guardar_respuesta(
            context,
            respuesta,
        )

        await mensaje.reply_text(respuesta)
        return

    context.user_data[
        "lumi_esperando_musica"
    ] = False

    context.user_data[
        "lumi_musica_confirmacion_pendiente"
    ] = None

    context.user_data[
        "lumi_ultima_consulta_musical"
    ] = consulta

    # Evitar utilizar los metadatos de otra
    # canción si esta búsqueda no encuentra nada.
    context.user_data[
        "lumi_ultima_cancion"
    ] = None

    await mostrar_escribiendo(
        update,
        context,
    )

    try:
        cancion = await asyncio.to_thread(
            buscar_cancion,
            consulta,
        )

    except Exception:
        logger.exception(
            "No se pudo completar la búsqueda musical."
        )
        cancion = None

    if not cancion:
        respuesta = (
            "💜 No encontré una coincidencia "
            "en el catálogo musical. "
            "Prueba con el título y el artista, "
            "o con otra versión."
        )

        guardar_respuesta(
            context,
            respuesta,
        )

        await mensaje.reply_text(respuesta)
        return

    context.user_data[
        "lumi_ultima_cancion"
    ] = {
        "titulo": cancion.get("titulo", ""),
        "artista": cancion.get("artista", ""),
        "album": cancion.get("album", ""),
        "fecha": cancion.get("fecha", ""),
    }

    respuesta = formatear_cancion(cancion)

    if sorpresa:
        respuesta = (
            "🎲 ¡Aquí tienes una sorpresa musical! 💜\n\n"
            + respuesta
        )

    guardar_respuesta(
        context,
        respuesta,
    )

    try:
        await enviar_resultado_musical(
            mensaje,
            cancion,
            sorpresa=sorpresa,
        )

    except Exception:
        logger.exception(
            "No se pudo enviar completamente "
            "el resultado musical."
        )

        await mensaje.reply_text(
            "💜 Encontré la canción, pero hubo "
            "un problema al enviar alguno de "
            "sus enlaces. Puedes intentarlo de nuevo."
        )


# ============================================================
# CORRECCIONES MUSICALES
# ============================================================

async def responder_correccion_musical(
    update,
    context,
    correccion,
):
    """
    Corrige una búsqueda musical anterior.

    Ejemplo:
        Black Betty / Spiderbait
        "Es la de Ram Jam"
        -> Black Betty Ram Jam
    """
    mensaje = update.effective_message

    if mensaje is None:
        return

    consulta_anterior = context.user_data.get(
        "lumi_ultima_consulta_musical",
        "",
    )

    ultima = context.user_data.get(
        "lumi_ultima_cancion"
    ) or {}

    if not consulta_anterior:
        return

    consulta_corregida = construir_consulta_corregida(
        consulta_anterior,
        correccion,
        titulo_anterior=ultima.get(
            "titulo", ""
        ),
        artista_anterior=ultima.get(
            "artista", ""
        ),
    )

    if not consulta_corregida:
        await mensaje.reply_text(
            "💜 ¿Qué canción o versión buscabas?"
        )
        return

    logger.info(
        "Corrección musical: %s -> %s",
        consulta_anterior,
        consulta_corregida,
    )

    await mensaje.reply_text(
        "🎶💜 ¡Entendido! Buscaré "
        f"«{consulta_corregida}»."
    )

    # Ejecutamos la búsqueda en este mismo turno.
    await responder_con_musica(
        update,
        context,
        consulta_corregida,
    )


# ============================================================
# CONFIRMACIÓN MUSICAL PENDIENTE
# ============================================================

async def procesar_confirmacion_musical(
    update,
    context,
    texto,
):
    """
    Procesa una confirmación únicamente cuando
    existe una consulta musical pendiente.

    Devuelve True si gestionó el mensaje.
    """
    pendiente = context.user_data.get(
        "lumi_musica_confirmacion_pendiente"
    )

    if not pendiente:
        return False

    if es_confirmacion_musical(texto):
        context.user_data[
            "lumi_musica_confirmacion_pendiente"
        ] = None

        await responder_con_musica(
            update,
            context,
            pendiente,
        )
        return True

    if es_cancelacion_musical(texto):
        context.user_data[
            "lumi_musica_confirmacion_pendiente"
        ] = None

        await update.effective_message.reply_text(
            "💜 ¡Entendido! No buscaré esa canción."
        )
        return True

    # Un mensaje distinto cancela la confirmación
    # para evitar búsquedas inesperadas.
    context.user_data[
        "lumi_musica_confirmacion_pendiente"
    ] = None

    return False


# ============================================================
# HANDLER PRINCIPAL
# ============================================================

async def responder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Procesa los mensajes escritos de Lumi.

    Orden:
    1. Memoria.
    2. Machine Learning.
    3. Música explícita.
    4. Música sorpresa.
    5. Correcciones musicales.
    6. Confirmaciones pendientes.
    7. Preguntas sobre canciones.
    8. Respuestas habladas.
    9. Música pendiente.
    10. Gemini y consultas de tiempo.
    """
    mensaje = update.effective_message

    if mensaje is None or not mensaje.text:
        return

    texto = mensaje.text.strip()

    if not texto:
        return

    logger.info(
        "Procesando mensaje escrito en el chat %s.",
        (
            update.effective_chat.id
            if update.effective_chat
            else "desconocido"
        ),
    )

    # --------------------------------------------------------
    # 1. MEMORIA DE LA ÚLTIMA RESPUESTA
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 2. ANÁLISIS DE MACHINE LEARNING
    # --------------------------------------------------------

    texto_analisis = extraer_mensaje_analisis(
        texto
    )

    if texto_analisis is not None:
        context.user_data[
            "lumi_esperando_musica"
        ] = False

        if not texto_analisis:
            await mensaje.reply_text(
                "💜 Claro. Envíame el mensaje "
                "que quieres que analice."
            )
            return

        await responder_con_analisis(
            update,
            context,
            texto_analisis,
        )
        return

    # --------------------------------------------------------
    # 3. SOLICITUDES MUSICALES EXPLÍCITAS
    # --------------------------------------------------------

    peticion_musica = extraer_peticion_musica(
        texto
    )

    if peticion_musica is not None:
        await responder_con_musica(
            update,
            context,
            peticion_musica,
            sorpresa=es_sorpresa_musical(texto),
        )
        return

    # --------------------------------------------------------
    # 4. MÚSICA SORPRESA
    # --------------------------------------------------------

    if es_sorpresa_musical(texto):
        await responder_con_musica(
            update,
            context,
            "",
            sorpresa=True,
        )
        return

    # --------------------------------------------------------
    # 5. CORRECCIONES MUSICALES
    # --------------------------------------------------------

    consulta_anterior = context.user_data.get(
        "lumi_ultima_consulta_musical"
    )

    if consulta_anterior:
        correccion = extraer_correccion_musica(
            texto
        )

        if correccion is not None:
            await responder_correccion_musical(
                update,
                context,
                correccion,
            )
            return

    # --------------------------------------------------------
    # 6. CONFIRMACIONES MUSICALES PENDIENTES
    # --------------------------------------------------------

    if await procesar_confirmacion_musical(
        update,
        context,
        texto,
    ):
        return

    # --------------------------------------------------------
    # 7. PREGUNTAS SOBRE LA ÚLTIMA CANCIÓN
    # --------------------------------------------------------

    ultima = context.user_data.get(
        "lumi_ultima_cancion"
    )

    if (
        ultima
        and es_pregunta_sobre_ultima_cancion(texto)
    ):
        context.user_data[
            "lumi_esperando_musica"
        ] = False

        contexto_cancion = (
            "La canción a la que se refiere "
            "el usuario es "
            f"'{ultima.get('titulo', '')}' "
            f"de {ultima.get('artista', '')}, "
            "del álbum "
            f"'{ultima.get('album', '')}' "
            "(fecha del catálogo: "
            f"{ultima.get('fecha', '')}). "
            f"Pregunta: {texto}"
        )

        await responder_con_gemini(
            update,
            context,
            contexto_cancion,
        )
        return

    # --------------------------------------------------------
    # 8. RESPUESTAS HABLADAS
    # --------------------------------------------------------

    peticion_audio = extraer_peticion_audio(
        texto
    )

    if peticion_audio is not None:
        context.user_data[
            "lumi_esperando_musica"
        ] = False

        if not peticion_audio:
            await mensaje.reply_text(
                "🎙️ ¡Claro! ¿Sobre qué tema "
                "quieres que te hable?"
            )
            return

        await responder_con_gemini(
            update,
            context,
            peticion_audio,
            por_voz=True,
        )
        return

    # --------------------------------------------------------
    # 9. RESPUESTA MUSICAL PENDIENTE
    # --------------------------------------------------------

    if context.user_data.get(
        "lumi_esperando_musica"
    ):
        limpio = normalizar_musica(
            texto
        ).strip(" ¿?¡!.,")

        if limpio in {
            "cancelar",
            "cancela",
            "olvidalo",
            "no gracias",
        }:
            context.user_data[
                "lumi_esperando_musica"
            ] = False

            await mensaje.reply_text(
                "💜 ¡Perfecto! Dejamos "
                "la música para después."
            )
            return

        if es_respuesta_musical_pendiente(texto):
            await responder_con_musica(
                update,
                context,
                texto,
            )
            return

        context.user_data[
            "lumi_esperando_musica"
        ] = False

    # --------------------------------------------------------
    # 10. GEMINI Y CONSULTAS DE TIEMPO
    # --------------------------------------------------------

    await responder_con_gemini(
        update,
        context,
        texto,
    )
