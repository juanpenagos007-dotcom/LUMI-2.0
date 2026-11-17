# ============================================================
# LUMI 💜
# UTILIDADES DE TEXTO Y FORMATO PARA TELEGRAM
# ============================================================

import html
import logging
import random
import re
import unicodedata

from telegram.constants import ParseMode
from telegram.error import TelegramError

from config import MAX_MENSAJE


logger = logging.getLogger("Lumi.texto")


# ============================================================
# ESCAPAR TEXTO PARA HTML
# ============================================================

def escapar(texto):
    """
    Escapa caracteres especiales para que Telegram
    pueda interpretar correctamente el formato HTML.
    """
    return html.escape(str(texto), quote=False)


# ============================================================
# ELEGIR TEXTO ALEATORIO
# ============================================================

def elegir_texto(opciones):
    """
    Selecciona una respuesta aleatoria de una lista.
    """
    return random.choice(opciones) if opciones else ""


# ============================================================
# NORMALIZACIÓN DE TEXTO
# ============================================================

def normalizar(texto):
    """
    Convierte el texto a minúsculas, elimina tildes,
    signos de puntuación y espacios repetidos.

    Ejemplo:
        "¡Lumi, Explícame con tu VOZ!"
        -> "lumi explicame con tu voz"
    """
    texto = str(texto or "").lower().strip()

    texto = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )

    texto = re.sub(r"[¿?¡!.,;:]", " ", texto)

    return re.sub(r"\s+", " ", texto).strip()


# ============================================================
# CONVERSIÓN DE MARKDOWN A HTML PARA TELEGRAM
# ============================================================

def markdown_a_html(texto):
    """
    Convierte Markdown básico a HTML compatible
    con Telegram.

    Formatos admitidos:
        **negrita**
        *cursiva*
        _cursiva_
        ~~tachado~~
        `codigo`
        ```python
        codigo en bloque
        ```
        # Encabezados
        - Listas
    """

    resultado = []
    dentro_codigo = False
    codigo = []
    idioma = ""

    def convertir_linea(linea):
        partes = re.split(r"(`[^`\n]+`)", linea)
        salida = []

        for parte in partes:
            if (
                parte.startswith("`")
                and parte.endswith("`")
                and len(parte) > 2
            ):
                salida.append(
                    "<code>"
                    + escapar(parte[1:-1])
                    + "</code>"
                )
                continue

            parte = escapar(parte)

            parte = re.sub(
                r"\*\*(.+?)\*\*",
                r"<b>\1</b>",
                parte,
            )

            parte = re.sub(
                r"(?<!\*)\*([^*\n]+)\*(?!\*)",
                r"<i>\1</i>",
                parte,
            )

            parte = re.sub(
                r"(?<!_)_([^_\n]+)_(?!_)",
                r"<i>\1</i>",
                parte,
            )

            parte = re.sub(
                r"~~(.+?)~~",
                r"<s>\1</s>",
                parte,
            )

            salida.append(parte)

        return "".join(salida)

    for linea in str(texto).splitlines():

        marcador = re.match(
            r"^\s*```([a-zA-Z0-9_+-]*)\s*$",
            linea,
        )

        if marcador:
            if dentro_codigo:
                contenido = escapar("\n".join(codigo))

                if idioma:
                    resultado.append(
                        '<pre><code class="language-'
                        + idioma
                        + '">'
                        + contenido
                        + "</code></pre>"
                    )
                else:
                    resultado.append(
                        "<pre>"
                        + contenido
                        + "</pre>"
                    )

                codigo = []
                idioma = ""
                dentro_codigo = False

            else:
                idioma = marcador.group(1)
                dentro_codigo = True

            continue

        if dentro_codigo:
            codigo.append(linea)
            continue

        titulo = re.match(
            r"^\s{0,3}#{1,6}\s+(.+)$",
            linea,
        )

        if titulo:
            resultado.append(
                "<b>"
                + convertir_linea(titulo.group(1))
                + "</b>"
            )
            continue

        vineta = re.match(
            r"^\s*[-*+]\s+(.+)$",
            linea,
        )

        if vineta:
            resultado.append(
                "• "
                + convertir_linea(vineta.group(1))
            )
            continue

        resultado.append(convertir_linea(linea))

    # Cerrar un bloque de código si quedó abierto.
    if dentro_codigo:
        resultado.append(
            "<pre>"
            + escapar("\n".join(codigo))
            + "</pre>"
        )

    return "\n".join(resultado).strip()


# ============================================================
# DIVIDIR Y ENVIAR MENSAJES LARGOS
# ============================================================

async def enviar_texto_largo(mensaje, texto):
    """
    Envía respuestas extensas a Telegram,
    dividiéndolas en fragmentos seguros.

    Intenta conservar el formato Markdown.
    Si Telegram rechaza el HTML, utiliza texto plano.
    """

    texto = str(texto or "").strip()

    if not texto:
        texto = "💜 No pude generar una respuesta esta vez."

    pendientes = texto.splitlines(keepends=True)

    grupos = []
    actual = ""

    for linea in pendientes:

        if len(actual + linea) <= MAX_MENSAJE:
            actual += linea
            continue

        if actual:
            grupos.append(actual)
            actual = ""

        while len(linea) > MAX_MENSAJE:
            grupos.append(linea[:MAX_MENSAJE])
            linea = linea[MAX_MENSAJE:]

        actual = linea

    if actual:
        grupos.append(actual)

    for grupo in grupos:
        convertido = markdown_a_html(grupo)

        try:
            if len(convertido) > 4096:
                raise ValueError(
                    "HTML demasiado largo para Telegram."
                )

            await mensaje.reply_text(
                convertido,
                parse_mode=ParseMode.HTML,
            )

        except (TelegramError, ValueError) as error:

            logger.warning(
                "No se pudo enviar el mensaje con HTML: %s",
                error,
            )

            await mensaje.reply_text(
                grupo[:MAX_MENSAJE]
            )
