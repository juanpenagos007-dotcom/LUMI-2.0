import os
import re
import html
import asyncio
import logging
import random
import unicodedata

from pathlib import Path
from dotenv import load_dotenv

# ============================================================
# Lumi antes 💜
# Telegram + Gemini + Machine Learning + Whisper + Cartesia
# ============================================================

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.error import TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from predict import analizar_texto
from services.conversacion import conversar, analizar_imagen
from services.audio_service import transcribir_audio
from services.voz_service import generar_voz


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger("LightBy")

TOKEN = os.getenv("TELEGRAM_TOKEN")

MAX_MENSAJE = 3900
MAX_ANALISIS = 2500
MAX_IMAGEN_BYTES = 10 * 1024 * 1024
MAX_AUDIO_BYTES = 10 * 1024 * 1024


# ============================================================
# PERSONALIDAD DEL ANÁLISIS
# ============================================================

ANALISIS = {
    "celebracion": {
        "emoji": "🎉",
        "titulo": "¡Hay motivos para celebrar!",
        "introduccion": "Este mensaje parece compartir una experiencia positiva.",
        "interpretaciones": [
            "La persona parece estar compartiendo un logro o una buena noticia.",
            "Las palabras reflejan satisfacción por algo que consiguió.",
            "El mensaje transmite entusiasmo por una experiencia positiva.",
        ],
        "sugerencias": [
            "¡Qué alegría! Felicidades por ese logro.",
            "¡Qué buena noticia! Me alegra que haya salido bien.",
        ],
    },
    "agradecimiento": {
        "emoji": "💜",
        "titulo": "Un mensaje de gratitud",
        "introduccion": "Aquí encuentro palabras de agradecimiento.",
        "interpretaciones": [
            "La persona está expresando agradecimiento por algo que valora.",
            "El mensaje reconoce una ayuda o un gesto positivo.",
        ],
        "sugerencias": [
            "¡Con mucho gusto! Me alegra haberte ayudado.",
            "¡Qué bueno haber podido ayudarte!",
        ],
    },
    "afecto": {
        "emoji": "💕",
        "titulo": "Palabras llenas de cariño",
        "introduccion": "Este mensaje contiene expresiones de afecto.",
        "interpretaciones": [
            "Las palabras expresan cariño o aprecio hacia otra persona.",
            "Parece una manera de comunicar cercanía o afecto.",
        ],
        "sugerencias": [
            "Gracias por expresar lo que sientes.",
            "Qué bonito que puedas comunicar tu aprecio.",
        ],
    },
    "tristeza": {
        "emoji": "🌧️",
        "titulo": "Un mensaje que merece comprensión",
        "introduccion": "El mensaje parece expresar un momento difícil.",
        "interpretaciones": [
            "El mensaje expresa tristeza o desánimo.",
            "Las palabras sugieren un momento emocionalmente difícil.",
        ],
        "sugerencias": [
            "Lamento que estés pasando por eso. ¿Quieres contarme qué ocurrió?",
            "Gracias por contarme cómo te sientes.",
        ],
    },
    "reclamo": {
        "emoji": "💭",
        "titulo": "Hay algo que necesita aclararse",
        "introduccion": "Este mensaje parece expresar una molestia.",
        "interpretaciones": [
            "La persona parece estar expresando inconformidad.",
            "El mensaje contiene un reclamo que podría necesitar una conversación.",
        ],
        "sugerencias": [
            "Entiendo que esto te haya molestado. ¿Podemos hablarlo con calma?",
            "Gracias por decírmelo. Quisiera entender mejor qué pasó.",
        ],
    },
    "celos": {
        "emoji": "🔎",
        "titulo": "Preguntas que pueden reflejar inquietud",
        "introduccion": "El mensaje podría relacionarse con dudas o inseguridad.",
        "interpretaciones": [
            "Las palabras podrían expresar preocupación, sin confirmar celos.",
            "Parece haber preguntas sobre una situación personal.",
        ],
        "sugerencias": [
            "Podemos hablar de lo que te preocupa con tranquilidad.",
            "Es importante conversar con confianza y respeto.",
        ],
    },
    "agresion": {
        "emoji": "⚠️",
        "titulo": "Un mensaje con expresiones fuertes",
        "introduccion": "Detecté expresiones que podrían resultar ofensivas.",
        "interpretaciones": [
            "El lenguaje contiene expresiones hostiles.",
            "El tono parece confrontativo.",
        ],
        "sugerencias": [
            "Podemos hablar sin recurrir a los insultos.",
            "Prefiero que conversemos con respeto.",
        ],
    },
    "ruptura": {
        "emoji": "🍂",
        "titulo": "Una conversación delicada",
        "introduccion": "El mensaje parece hablar del final de una relación.",
        "interpretaciones": [
            "Las palabras expresan la posibilidad de finalizar una relación.",
            "El mensaje parece comunicar una separación importante.",
        ],
        "sugerencias": [
            "Gracias por hablarme con claridad.",
            "Entiendo que es una conversación importante.",
        ],
    },
    "manipulacion": {
        "emoji": "🚩",
        "titulo": "Una expresión que merece atención",
        "introduccion": "Algunas palabras podrían implicar presión emocional.",
        "interpretaciones": [
            "El mensaje podría generar culpa o presión.",
            "El contexto ayudaría a comprender la intención.",
        ],
        "sugerencias": [
            "Podemos hablar sin presionarnos.",
            "Es importante respetar los límites de cada persona.",
        ],
    },
    "control": {
        "emoji": "🛡️",
        "titulo": "Hablemos de confianza y límites",
        "introduccion": "El mensaje podría relacionarse con el control de otra persona.",
        "interpretaciones": [
            "Las palabras podrían exigir información personal.",
            "El mensaje puede relacionarse con límites y privacidad.",
        ],
        "sugerencias": [
            "Podemos hablar respetando nuestra privacidad.",
            "La confianza y el espacio personal son importantes.",
        ],
    },
    "desinteres": {
        "emoji": "🌙",
        "titulo": "Un mensaje que pide espacio",
        "introduccion": "Este mensaje podría expresar pocas ganas de conversar.",
        "interpretaciones": [
            "La persona podría no querer continuar hablando ahora.",
            "El mensaje podría indicar necesidad de espacio.",
        ],
        "sugerencias": [
            "Está bien, podemos hablar en otro momento.",
            "Entiendo. Cuando quieras conversar, me dices.",
        ],
    },
    "curiosidad": {
        "emoji": "🔍",
        "titulo": "¡La curiosidad está presente!",
        "introduccion": "Este mensaje parece buscar información.",
        "interpretaciones": [
            "La persona está haciendo una pregunta.",
            "El mensaje invita a aclarar una duda.",
        ],
        "sugerencias": [
            "¡Claro! Cuéntame un poquito más.",
            "¡Buena pregunta! Te cuento lo que sé.",
        ],
    },
    "saludo": {
        "emoji": "👋",
        "titulo": "¡Una conversación está comenzando!",
        "introduccion": "Este mensaje parece iniciar una conversación.",
        "interpretaciones": [
            "Es un saludo cordial.",
            "La persona busca establecer contacto.",
        ],
        "sugerencias": [
            "¡Holaaa! ¿Cómo te va?",
            "¡Hey! ¿Cómo estás?",
        ],
    },
    "despedida": {
        "emoji": "🌟",
        "titulo": "Una despedida cordial",
        "introduccion": "Este mensaje parece cerrar una conversación.",
        "interpretaciones": [
            "La persona está despidiéndose.",
            "El mensaje expresa una despedida natural.",
        ],
        "sugerencias": [
            "¡Nos vemos! Que tengas un bonito día.",
            "¡Hasta luego! Cuídate mucho.",
        ],
    },
    "normal": {
        "emoji": "💬",
        "titulo": "Un mensaje para explorar",
        "introduccion": "A veces necesitamos más contexto.",
        "interpretaciones": [
            "No encuentro una intención específica mediante las reglas actuales.",
            "El mensaje puede interpretarse de distintas maneras.",
        ],
        "sugerencias": [
            "¡Entiendo! Cuéntame un poquito más.",
            "Gracias por contármelo.",
        ],
    },
}

EMOJIS_EMOCION = {
    "alegria": "😊",
    "positivo": "😊",
    "tristeza": "😢",
    "enojo": "😠",
    "sorpresa": "😲",
    "disgusto": "😖",
    "miedo": "😨",
    "neutral": "😐",
}

NOMBRES_EMOCION = {
    "alegria": "Alegría",
    "positivo": "Alegría",
    "tristeza": "Tristeza",
    "enojo": "Enojo",
    "sorpresa": "Sorpresa",
    "disgusto": "Disgusto",
    "miedo": "Miedo",
    "neutral": "Neutral",
}

NOMBRES_INTENCION = {
    "celebracion": "Celebrar un logro",
    "agradecimiento": "Expresar gratitud",
    "afecto": "Expresar cariño",
    "tristeza": "Expresar tristeza",
    "reclamo": "Expresar inconformidad",
    "celos": "Posible inquietud",
    "agresion": "Expresión hostil",
    "ruptura": "Hablar de una separación",
    "manipulacion": "Posible presión emocional",
    "control": "Posible control",
    "desinteres": "Pedir espacio",
    "curiosidad": "Hacer una pregunta",
    "saludo": "Saludar",
    "despedida": "Despedirse",
    "normal": "No determinada",
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def escapar(texto):
    return html.escape(str(texto), quote=False)


def elegir_texto(opciones):
    return random.choice(opciones) if opciones else ""


def normalizar(texto):
    texto = str(texto or "").lower().strip()
    texto = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    texto = re.sub(r"[¿?¡!.,;:]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def extraer_peticion_audio(texto):
    """
    Detecta solicitudes escritas para recibir una respuesta hablada.

    Devuelve:
        None: no se pidió una respuesta hablada.
        "": se pidió audio, pero no se indicó el tema.
        str: pregunta o instrucción limpia para Gemini.

    No modifica el funcionamiento de las notas de voz recibidas.
    """
    original = str(texto or "").strip()

    if not original:
        return None

    normalizado = normalizar(original)

    # Eliminar el nombre de la asistente al comienzo.
    normalizado = re.sub(
        r"^(?:(?:oye|hola|hey|buenas)\s+)?"
        r"(?:(?:lumi|l u m i|lightby|light by|lightboy)"
        r"\s+)?"
        r"(?:(?:por favor)\s+)?",
        "",
        normalizado,
    ).strip()

    # Una prohibición explícita tiene prioridad.
    negativas = [
        r"\bno (?:me )?(?:mandes|envies|envíes|"
        r"respondas|contestes|hables)\b.{0,35}"
        r"\b(?:audio|voz|hablando)\b",

        r"\b(?:sin audio|solo texto|solamente texto|"
        r"por escrito|no quiero audio|no uses tu voz)\b",

        r"\b(?:prefiero|quiero|necesito)\b"
        r".{0,20}\b(?:texto|escrito)\b",
    ]

    if any(re.search(p, normalizado) for p in negativas):
        return None

    # Formas explícitas de solicitar una respuesta hablada.
    patrones = [
        # "Dime en un audio qué es Python"
        r"\b(?:dime|cuentame|explicame|respondeme|"
        r"contesta|contestame|responde|hablame|"
        r"leeme|di|explica|cuenta)\s+"
        r"(?:en\s+(?:un\s+)?audio|"
        r"con\s+(?:tu\s+)?voz|"
        r"por\s+(?:audio|voz)|hablando)\b",

        # "Explícame qué es Python en un audio"
        r"\b(?:en\s+(?:un\s+)?audio|"
        r"con\s+(?:tu\s+)?voz|"
        r"por\s+(?:audio|voz))\s*$",

        # "Quiero que me respondas con tu voz"
        r"\b(?:quiero|necesito|prefiero|me gustaria)"
        r"\s+(?:que\s+)?(?:me\s+)?"
        r"(?:respondas|contestes|expliques|digas|"
        r"cuentes|hables)\b.{0,35}"
        r"\b(?:audio|voz|hablando)\b",

        # "Puedes explicarme por voz..."
        r"\b(?:puedes|podrias|podrías)\s+"
        r"(?:decirme|explicarme|responderme|"
        r"contestarme|contarme|hablarme|leerme)"
        r"\s+(?:en\s+(?:un\s+)?audio|"
        r"con\s+(?:tu\s+)?voz|por\s+(?:audio|voz))\b",

        # "Mándame un audio explicando..."
        r"\b(?:mandame|enviame|pasame|"
        r"mandame|envia|envíame)\s+"
        r"(?:una?\s+)?"
        r"(?:nota\s+de\s+voz|mensaje\s+de\s+voz|"
        r"audio|mensaje\s+de\s+audio)\b",

        # "Respóndeme hablando"
        r"\b(?:responde|respondeme|contestame|"
        r"explicame|cuentame|dime)\s+hablando\b",

        # "Quiero escucharte explicar..."
        r"\b(?:quiero|me gustaria|prefiero)\s+"
        r"(?:escucharte|oirte)\s+"
        r"(?:explicar|contar|decir|hablar|responder)\b",

        # "Háblame sobre..."
        r"^(?:hablame|habla)\s+"
        r"(?:sobre|acerca de|de)\s+",

        # "¿Me lo dices hablando?"
        r"\b(?:me lo|dimelo|dilo|cuentamelo)"
        r"\s+(?:puedes\s+)?"
        r"(?:decir|explicar|contar)?"
        r"\s*(?:hablando|con tu voz|por audio)\b",

        # "Dame una respuesta en audio"
        r"\b(?:dame|quiero|necesito)\s+"
        r"(?:una?\s+)?"
        r"(?:respuesta|explicacion|mensaje)\s+"
        r"(?:en\s+audio|hablada|por\s+voz)\b",

        # "Respóndeme por audio"
        r"\b(?:respondeme|responde|contestame|"
        r"contesta)\s+por\s+audio\b",
    ]

    coincidencias = []

    for patron in patrones:
        coincidencia = re.search(patron, normalizado)

        if coincidencia:
            coincidencias.append(coincidencia)

    if not coincidencias:
        return None

    # Elegir la coincidencia más extensa.
    coincidencia = max(
        coincidencias,
        key=lambda m: m.end() - m.start(),
    )

    # Eliminar solamente la instrucción de modalidad.
    pregunta = (
        normalizado[:coincidencia.start()]
        + " "
        + normalizado[coincidencia.end():]
    )

    pregunta = re.sub(r"\s+", " ", pregunta).strip()

    # Limpiar conectores sobrantes.
    pregunta = re.sub(
        r"^(?:que\s+me\s+)?"
        r"(?:sobre|acerca de)\s+",
        "",
        pregunta,
    )

    pregunta = re.sub(
        r"^(?:por favor|quiero saber|"
        r"me gustaria saber)\s+",
        "",
        pregunta,
    )

    pregunta = pregunta.strip(" :,.¿?¡!")

    # Si solo se solicitó un audio, preguntar el tema.
    return pregunta



def extraer_mensaje_analisis(texto):
    """
    Detecta solicitudes de análisis de Machine Learning.
    Compatible con mensajes escritos y transcripciones de Whisper.
    """
    texto = str(texto or "").strip()

    patron = (
        r"^\s*"
        r"(?:(?:oye|hola|hey)\s+)?"
        r"(?:lumi|l\.?\s*u\.?\s*m\.?\s*i\.?|light\s*by|lightby|lightboy|light boy)?"
        r"\s*[,.:!¿?]*\s*"
        r"(?:(?:por favor)\s*[,.:]?\s*)?"
        r"(?:analiza|analízame|analizame|"
        r"puedes analizar|podrías analizar|podrias analizar)"
        r"\s+"
        r"(?:"
        r"(?:este|esta|mi|el siguiente|la siguiente)\s+"
        r"(?:mensaje|respuesta|texto|frase)"
        r"|lo siguiente"
        r")"
        r"\s*[:,.\-]?\s*(.+?)\s*[.!?]*\s*$"
    )

    coincidencia = re.match(
        patron,
        texto,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if coincidencia:
        contenido = coincidencia.group(1).strip()
        return contenido if contenido else None

    return None




def detectar_peticion_anterior(texto):
    texto = normalizar(texto)

    texto = re.sub(
        r"^(?:(?:oye|hola|hey)\s+)?"
        r"(?:(?:lumi|l u m i|lightby|light by)"
        r"\s+)?",
        "",
        texto,
    ).strip()

    patrones_texto = [
        r"\b(?:escribeme|escribe|pasame|mandame|"
        r"enviame)\b.{0,50}"
        r"\b(?:ultimo|respuesta|dijiste|"
        r"anterior|eso|lo mismo)\b",

        r"\b(?:no entendi|no comprendi)\b"
        r".{0,50}\b(?:escribe|texto|escrito)\b",

        r"\b(?:lo ultimo|respuesta anterior|"
        r"lo que dijiste|eso)\b"
        r".{0,35}\b(?:texto|escrito)\b",

        r"^(?:mejor\s+)?(?:escribemelo|"
        r"pasamelo por escrito|dimelo por escrito)$",
    ]

    if any(re.search(p, texto) for p in patrones_texto):
        return "texto"

    patrones_audio = [
        r"\b(?:repite|repiteme|repetir)\b"
        r".{0,50}\b(?:ultimo|respuesta|"
        r"dijiste|anterior|otra vez|audio|voz)\b",

        r"^(?:repite|repiteme|otra vez|"
        r"puedes repetir|repitelo)$",

        r"\b(?:vuelve a decir|dimelo otra vez|"
        r"dilo otra vez)\b",

        r"\b(?:leeme|lee|dime|cuentame|"
        r"repiteme)\b.{0,45}"
        r"\b(?:ultimo|anterior|respuesta|"
        r"eso|lo mismo|lo que dijiste)\b"
        r".{0,35}\b(?:audio|voz|hablando)\b",

        r"\b(?:lo ultimo|respuesta anterior|"
        r"lo que dijiste|eso|lo mismo)\b"
        r".{0,35}\b(?:audio|voz|hablando)\b",

        r"^(?:leemelo|dimelo en audio|"
        r"dimelo con tu voz|"
        r"repitelo en audio|"
        r"leeme eso|"
        r"quiero escucharlo|"
        r"quiero oirlo)$",
    ]

    if any(re.search(p, texto) for p in patrones_audio):
        return "audio"

    return None


def guardar_respuesta(context, texto):
    if texto:
        context.chat_data["ultima_respuesta"] = str(texto)


def obtener_confianza(confianza):
    try:
        valor = float(confianza)
    except (TypeError, ValueError):
        return "No disponible"

    if valor <= 0:
        return "Ajustada mediante análisis contextual"

    return f"{max(0, min(100, valor)):.0f}%"


def obtener_toxicidad(toxicidad):
    if str(toxicidad).lower() == "si":
        return "🔴 Posibles señales detectadas"
    return "🟢 Sin señales detectadas"


def obtener_riesgo(riesgo):
    valor = str(riesgo).lower()
    for clave, etiqueta in {
        "alto": "🔴 Alto",
        "medio": "🟡 Medio",
        "bajo": "🟢 Bajo",
    }.items():
        if clave in valor:
            return etiqueta
    return escapar(riesgo)


def obtener_evasion(ghosting):
    try:
        valor = float(ghosting)
    except (TypeError, ValueError):
        return "No determinada"

    if valor >= 40:
        return "Señales de querer interrumpir la conversación"
    if valor > 0:
        return "Posible necesidad de espacio"
    return "Sin señales específicas"


# ============================================================
# ANÁLISIS EMOCIONAL
# ============================================================

def formatear_analisis(
    emocion, toxicidad, ghosting,
    riesgo, intencion, confianza
):
    contenido = ANALISIS.get(intencion, ANALISIS["normal"])

    nombre_emocion = NOMBRES_EMOCION.get(
        emocion, str(emocion).capitalize()
    )
    nombre_intencion = NOMBRES_INTENCION.get(
        intencion, "No determinada"
    )

    lineas = [
        f'{contenido["emoji"]} <b>{escapar(contenido["titulo"])}</b>',
        "",
        escapar(contenido["introduccion"]),
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "🧠 <b>LO QUE DESCUBRÍ</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        f'{EMOJIS_EMOCION.get(emocion, "🧠")} '
        f'<b>Emoción:</b> {escapar(nombre_emocion)}',
        f'🎯 <b>Intención:</b> {escapar(nombre_intencion)}',
        f'🛡️ <b>Toxicidad:</b> {obtener_toxicidad(toxicidad)}',
        f'🌱 <b>Riesgo estimado:</b> {obtener_riesgo(riesgo)}',
        f'📊 <b>Confianza:</b> {escapar(obtener_confianza(confianza))}',
    ]

    if intencion == "desinteres":
        lineas.extend([
            "",
            "💭 <b>Indicador de evasión:</b> "
            + escapar(obtener_evasion(ghosting)),
        ])

    lineas.extend([
        "",
        "💡 <b>¿QUÉ PODRÍA SIGNIFICAR?</b>",
        "",
        escapar(elegir_texto(contenido["interpretaciones"])),
        "",
        "💬 <b>¿CÓMO PODRÍAS RESPONDER?</b>",
        "",
        "<i>«"
        + escapar(elegir_texto(contenido["sugerencias"]))
        + "»</i>",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "💜 <b>Un detalle de LightBy</b>",
        "",
        "<i>Las palabras dan pistas sobre las emociones, "
        "pero no cuentan toda la historia. "
        "Este análisis es orientativo y puede equivocarse.</i>",
    ])

    return "\n".join(lineas)


def explicar_analisis_voz(
    emocion, toxicidad, ghosting,
    riesgo, intencion, confianza
):
    contenido = ANALISIS.get(intencion, ANALISIS["normal"])

    nombre_emocion = NOMBRES_EMOCION.get(
        emocion, str(emocion).capitalize()
    )
    nombre_intencion = NOMBRES_INTENCION.get(
        intencion, "No determinada"
    )

    partes = [
        "¡Claro! Ya analicé tu mensaje.",
        f"La emoción identificada es {nombre_emocion}.",
        f"La posible intención es {nombre_intencion}.",
    ]

    if str(toxicidad).lower() == "si":
        partes.append(
            "Encontré posibles señales de lenguaje hostil."
        )
    else:
        partes.append(
            "No detecté señales específicas de lenguaje hostil."
        )

    partes.append(f"El riesgo estimado es {riesgo}.")

    confianza_texto = obtener_confianza(confianza)
    if confianza_texto.endswith("%"):
        partes.append(
            f"La confianza estimada para la emoción es "
            f"de {confianza_texto.replace('%', ' por ciento')}."
        )

    if intencion == "desinteres":
        partes.append(obtener_evasion(ghosting) + ".")

    partes.append(
        elegir_texto(contenido["interpretaciones"])
    )

    partes.append(
        "Recuerda que este análisis es orientativo "
        "y puede equivocarse."
    )

    return " ".join(partes)


# ============================================================
# FORMATO DE RESPUESTAS DE GEMINI
# ============================================================

def markdown_a_html(texto):
    """
    Convierte Markdown básico a HTML compatible con Telegram.
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
                    "<code>" + escapar(parte[1:-1]) + "</code>"
                )
                continue

            parte = escapar(parte)
            parte = re.sub(
                r"\*\*(.+?)\*\*", r"<b>\1</b>", parte
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
                r"~~(.+?)~~", r"<s>\1</s>", parte
            )
            salida.append(parte)

        return "".join(salida)

    for linea in str(texto).splitlines():
        marcador = re.match(
            r"^\s*```([a-zA-Z0-9_+-]*)\s*$", linea
        )

        if marcador:
            if dentro_codigo:
                contenido = escapar("\n".join(codigo))
                if idioma:
                    resultado.append(
                        '<pre><code class="language-'
                        + idioma + '">'
                        + contenido + "</code></pre>"
                    )
                else:
                    resultado.append(
                        "<pre>" + contenido + "</pre>"
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
            r"^\s{0,3}#{1,6}\s+(.+)$", linea
        )
        if titulo:
            resultado.append(
                "<b>"
                + convertir_linea(titulo.group(1))
                + "</b>"
            )
            continue

        vineta = re.match(
            r"^\s*[-*+]\s+(.+)$", linea
        )
        if vineta:
            resultado.append(
                "• " + convertir_linea(vineta.group(1))
            )
            continue

        resultado.append(convertir_linea(linea))

    if dentro_codigo:
        resultado.append(
            "<pre>" + escapar("\n".join(codigo)) + "</pre>"
        )

    return "\n".join(resultado).strip()


async def enviar_texto_largo(mensaje, texto):
    texto = str(texto or "").strip()

    if not texto:
        texto = "💜 No pude generar una respuesta esta vez."

    # Divide el contenido en fragmentos seguros para Telegram.
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
                raise ValueError("HTML demasiado largo")

            await mensaje.reply_text(
                convertido,
                parse_mode=ParseMode.HTML,
            )
        except (TelegramError, ValueError):
            await mensaje.reply_text(grupo[:MAX_MENSAJE])


async def mostrar_escribiendo(update, context):
    if not update.effective_chat:
        return

    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )
    except TelegramError:
        logger.warning("No se pudo mostrar escritura.")


# ============================================================
# VOZ DE XIMENA - CARTESIA
# ============================================================

async def enviar_respuesta_hablada(mensaje, respuesta):
    ruta_audio = None

    try:
        ruta_audio = await generar_voz(respuesta)

        if not ruta_audio:
            raise RuntimeError(
                "No se generó el archivo de voz."
            )

        if not os.path.isfile(ruta_audio):
            raise FileNotFoundError(
                "No se encontró el audio generado."
            )

        tamano_mb = (
            os.path.getsize(ruta_audio) / (1024 * 1024)
        )

        logger.info(
            "🎙️ Enviando MP3 a Telegram: %.2f MB",
            tamano_mb,
        )

        with open(ruta_audio, "rb") as archivo:
            await mensaje.reply_audio(
                audio=archivo,
                filename="Lumi_AI.mp3",
                title="Lumi",
                performer="Lumi AI",
                read_timeout=180,
                write_timeout=180,
                connect_timeout=60,
            )
        logger.info(
            "✅ Respuesta de voz enviada correctamente."
        )

        return True

    except Exception:
        logger.exception(
            "❌ No se pudo generar o enviar la voz."
        )

        return False

    finally:
        if ruta_audio and os.path.exists(ruta_audio):
            try:
                os.remove(ruta_audio)
            except OSError:
                logger.warning(
                    "No se pudo eliminar el audio temporal."
                )


# ============================================================
# MEMORIA Y REPETICIÓN
# ============================================================

async def recuperar_ultima_respuesta(
    mensaje, context, tipo
):
    respuesta = context.chat_data.get("ultima_respuesta")

    if not respuesta:
        await mensaje.reply_text(
            "💜 Todavía no tengo una respuesta anterior "
            "para repetir. ¡Cuéntame algo primero!"
        )
        return

    if tipo == "texto":
        await enviar_texto_largo(mensaje, respuesta)
    else:
        await enviar_respuesta_hablada(mensaje, respuesta)


# ============================================================
# COMANDOS /start Y /ayuda
# ============================================================

async def bienvenida(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    mensaje = (
        "✨ <b>¡Bienvenido a Lumi! 💜</b>\n\n"
        "¡Holaaa! 👋 Soy <b>Lumi</b>, "
        "tu asistente de inteligencia artificial.\n\n"

        "💜 <b>¿Qué significa mi nombre?</b>\n"
        "L.U.M.I. significa:\n"
        "Lenguaje, Unión, Memoria e Inteligencia.\n\n"

        "💬 <b>Conversación:</b>\n"
        "Podemos hablar sobre tus ideas, "
        "dudas, estudios y proyectos.\n\n"

        "🧠 <b>Machine Learning:</b>\n"
        "Puedo analizar emociones y posibles "
        "intenciones de mensajes escritos.\n\n"

        "👁️ <b>Visión artificial:</b>\n"
        "También puedo analizar fotografías.\n\n"

        "🎙️ <b>Mi voz:</b>\n"
        "Puedes enviarme un audio y "
        "te responderé hablando.\n\n"

        "🔊 <b>¿Quieres escuchar una respuesta?</b>\n"
        "Escríbeme, por ejemplo:\n"
        "<i>Lumi, explícame por voz qué es Python.</i>\n\n"

        "🔁 <b>¿Quieres escucharme otra vez?</b>\n"
        "Dime: <i>Lumi, léeme lo último.</i>\n\n"

        "📝 <b>¿Prefieres leerlo?</b>\n"
        "Dime: <i>Escríbeme lo que dijiste.</i>\n\n"

        "💜 <b>Mi historia:</b>\n"
        "Fui creada por Juan Esteban "
        "Benítez Penagos, a quien llamo Beni.\n\n"

        "📚 Usa /ayuda para conocer mis funciones.\n\n"
        "✨ <i>Una luz para cada pregunta.</i>"
    )

    await update.message.reply_text(
        mensaje,
        parse_mode=ParseMode.HTML,
    )


async def ayuda(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    mensaje = (
        "💜 <b>GUÍA DE LUMI</b>\n\n"

        "💬 <b>Conversación:</b>\n"
        "Escríbeme normalmente y "
        "conversaremos sobre cualquier tema.\n\n"

        "🎙️ <b>Mensajes de voz:</b>\n"
        "Envíame un audio de máximo 2 minutos "
        "y te responderé con mi voz.\n\n"

        "🔊 <b>Respuestas habladas desde texto:</b>\n"
        "<code>Lumi, dime en un audio quién te creó</code>\n"
        "<code>Explícame con tu voz qué es Python</code>\n"
        "<code>Háblame sobre inteligencia artificial</code>\n"
        "<code>Quiero escucharte explicar qué es una API</code>\n"
        "<code>Mándame una nota de voz explicando React</code>\n\n"

        "🔁 <b>Escuchar una respuesta anterior:</b>\n"
        "<code>Lumi, léeme lo último</code>\n"
        "<code>Repítelo en audio</code>\n"
        "<code>Quiero escucharlo</code>\n\n"

        "📝 <b>Recuperar una respuesta escrita:</b>\n"
        "<code>Escríbeme lo que dijiste</code>\n"
        "<code>No entendí, escríbeme lo último</code>\n\n"

        "🧠 <b>Análisis de emociones:</b>\n"
        "<code>Analiza este mensaje: Estoy feliz.</code>\n\n"

        "<code>Analiza esta respuesta: "
        "No quiero hablar ahora.</code>\n\n"

        "🎧 También puedes darme instrucciones por voz.\n\n"

        "👁️ <b>Fotografías:</b>\n"
        "Envíame una imagen con una pregunta.\n\n"

        "⚠️ Los análisis emocionales son "
        "orientativos y pueden equivocarse.\n\n"

        "✨ <i>Una luz para cada pregunta.</i>"
    )

    await update.message.reply_text(
        mensaje,
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# CONVERSACIÓN CON GEMINI
# ============================================================


async def responder_con_gemini(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    texto: str,
    por_voz=False,
):
    await mostrar_escribiendo(update, context)

    respuesta = await asyncio.to_thread(
        conversar,
        texto,
    )

    if not respuesta:
        respuesta = (
            "💜 Esta vez no pude generar una respuesta. "
            "¿Podemos intentarlo nuevamente?"
        )

    # Guardar la respuesta para poder repetirla.
    guardar_respuesta(context, respuesta)

    # Si el usuario pidió audio, usar Cartesia.
    if por_voz:
        logger.info(
            "🎙️ MODO CARTESIA ACTIVADO DESDE TEXTO"
        )

        enviado = await enviar_respuesta_hablada(
            update.message,
            respuesta,
        )

        if enviado:
            return

        # Si falla la voz, conservar la respuesta escrita.
        await enviar_texto_largo(
            update.message,
            respuesta,
        )
        return

    # Conversación escrita normal.
    await enviar_texto_largo(
        update.message,
        respuesta,
    )



# ============================================================
# ANÁLISIS DE RUBIELA - MACHINE LEARNING
# ============================================================

async def responder_con_analisis(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    texto: str,
    por_voz=False,
):
    mensaje = update.message

    if not texto.strip():
        await mensaje.reply_text(
            "💜 Me falta el mensaje que quieres analizar.\n\n"
            "Ejemplo: Analiza este mensaje: Estoy feliz."
        )
        return

    if len(texto) > MAX_ANALISIS:
        await mensaje.reply_text(
            f"💜 Envíame un texto de máximo "
            f"{MAX_ANALISIS} caracteres."
        )
        return

    await mostrar_escribiendo(update, context)

    resultado = await asyncio.to_thread(
        analizar_texto, texto
    )

    if (
        not isinstance(resultado, (tuple, list))
        or len(resultado) != 6
    ):
        raise ValueError(
            "predict.py debe devolver seis valores."
        )

    (
        emocion,
        toxicidad,
        ghosting,
        riesgo,
        intencion,
        confianza,
    ) = resultado

    if por_voz:
        respuesta = explicar_analisis_voz(
            emocion,
            toxicidad,
            ghosting,
            riesgo,
            intencion,
            confianza,
        )

        enviado = await enviar_respuesta_hablada(
            mensaje, respuesta
        )

        if enviado:
            guardar_respuesta(context, respuesta)
        return

    respuesta = formatear_analisis(
        emocion,
        toxicidad,
        ghosting,
        riesgo,
        intencion,
        confianza,
    )

    await mensaje.reply_text(
        respuesta,
        parse_mode=ParseMode.HTML,
    )

    # Guardamos una versión legible sin etiquetas HTML.
    texto_plano = re.sub(r"<[^>]+>", "", respuesta)
    guardar_respuesta(context, html.unescape(texto_plano))


# ============================================================
# VISIÓN ARTIFICIAL
# ============================================================

async def recibir_imagen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    mensaje = update.message

    if not mensaje or not mensaje.photo:
        return

    try:
        await mostrar_escribiendo(update, context)

        foto = mensaje.photo[-1]

        if foto.file_size and foto.file_size > MAX_IMAGEN_BYTES:
            await mensaje.reply_text(
                "💜 Esa fotografía es demasiado grande."
            )
            return

        archivo = await context.bot.get_file(foto.file_id)
        contenido = await archivo.download_as_bytearray()
        imagen_bytes = bytes(contenido)

        if not imagen_bytes:
            await mensaje.reply_text(
                "💜 No pude leer esa fotografía."
            )
            return

        if len(imagen_bytes) > MAX_IMAGEN_BYTES:
            await mensaje.reply_text(
                "💜 La fotografía supera el tamaño permitido."
            )
            return

        pregunta = (mensaje.caption or "").strip()

        if not pregunta:
            pregunta = (
                "LightBy, ¿qué observas en esta fotografía? "
                "Describe los elementos principales."
            )

        respuesta = await asyncio.to_thread(
            analizar_imagen,
            imagen_bytes,
            pregunta,
        )

        await enviar_texto_largo(mensaje, respuesta)
        guardar_respuesta(context, respuesta)

    except Exception:
        logger.exception(
            "Error al analizar fotografía."
        )

        try:
            await mensaje.reply_text(
                "💜 Ups, tuve un problema al interpretar "
                "esa imagen. ¿Intentamos otra vez?"
            )
        except TelegramError:
            pass


# ============================================================
# OÍDOS DE LIGHTBY - WHISPER
# ============================================================


async def recibir_audio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    mensaje = update.message

    if not mensaje:
        return

    audio = mensaje.voice or mensaje.audio

    if not audio:
        return

    if audio.duration and audio.duration > 120:
        await mensaje.reply_text(
            "💜 Por ahora puedo escuchar audios "
            "de máximo 2 minutos."
        )
        return

    if audio.file_size and audio.file_size > MAX_AUDIO_BYTES:
        await mensaje.reply_text(
            "💜 Ese audio es demasiado grande."
        )
        return

    try:
        await mostrar_escribiendo(update, context)

        logger.info("🎧 LightBy recibió un audio.")

        archivo = await context.bot.get_file(audio.file_id)

        contenido = await archivo.download_as_bytearray()

        audio_bytes = bytes(contenido)

        if len(audio_bytes) > MAX_AUDIO_BYTES:
            await mensaje.reply_text(
                "💜 El audio supera el tamaño permitido."
            )
            return

        # 1. TRANSCRIPCIÓN CON WHISPER
        texto = await asyncio.to_thread(
            transcribir_audio,
            audio_bytes,
        )

        if not texto:
            await mensaje.reply_text(
                "💜 No pude reconocer claramente "
                "lo que dijiste. ¿Puedes repetirlo?"
            )
            return

        texto = str(texto).strip()

        logger.info(
            "🎧 WHISPER TRANSCRIBIÓ: %s",
            texto,
        )

        # 2. REPETIR O ESCRIBIR LA ÚLTIMA RESPUESTA
        peticion = detectar_peticion_anterior(texto)

        if peticion:
            logger.info(
                "🔁 Recuperando última respuesta: %s",
                peticion,
            )

            await recuperar_ultima_respuesta(
                mensaje,
                context,
                peticion,
            )
            return

        # 3. DETECTAR MACHINE LEARNING
        mensaje_analizar = extraer_mensaje_analisis(texto)

        if mensaje_analizar is not None:
            logger.info(
                "🧠 MODO MACHINE LEARNING ACTIVADO"
            )
            logger.info(
                "📩 Texto para predict.py: %s",
                mensaje_analizar,
            )

            await responder_con_analisis(
                update,
                context,
                mensaje_analizar,
                por_voz=True,
            )

            return

        # 4. CONVERSACIÓN NORMAL CON GEMINI
        logger.info(
            "💬 MODO GEMINI ACTIVADO"
        )

        respuesta = await asyncio.to_thread(
            conversar,
            texto,
        )

        if not respuesta:
            respuesta = (
                "Esta vez no pude generar una respuesta. "
                "¿Podemos intentarlo nuevamente?"
            )

        # 5. RESPONDER SOLO CON XIMENA
        enviado = await enviar_respuesta_hablada(
            mensaje,
            respuesta,
        )

        if enviado:
            guardar_respuesta(context, respuesta)

    except Exception:
        logger.exception(
            "❌ Error al procesar el audio."
        )

        try:
            await mensaje.reply_text(
                "💜 Tuve un problema al escuchar "
                "tu audio. ¿Intentamos nuevamente?"
            )
        except TelegramError:
            pass



# ============================================================
# MENSAJES ESCRITOS
# ============================================================


async def responder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    texto = (update.message.text or "").strip()

    if not texto:
        return

    try:
        logger.info("📩 TEXTO: %s", texto)

        # 1. Recuperar la última respuesta.
        peticion = detectar_peticion_anterior(texto)

        if peticion:
            logger.info(
                "🔁 RECUPERANDO RESPUESTA: %s",
                peticion,
            )

            await recuperar_ultima_respuesta(
                update.message,
                context,
                peticion,
            )
            return

        # 2. Detectar solicitud de Machine Learning.
        mensaje_analizar = extraer_mensaje_analisis(texto)

        if mensaje_analizar is not None:
            logger.info(
                "🧠 MODO MACHINE LEARNING (TEXTO)"
            )

            await responder_con_analisis(
                update,
                context,
                mensaje_analizar,
                por_voz=False,
            )
            return

        # 3. Detectar si el usuario solicita audio.
        pregunta_audio = extraer_peticion_audio(texto)

        if pregunta_audio is not None:
            logger.info(
                "🎙️ SOLICITUD DE AUDIO DETECTADA"
            )

            if not pregunta_audio:
                await update.message.reply_text(
                    "💜 ¡Claro! ¿Qué quieres que "
                    "te diga con mi voz?"
                )
                return

            logger.info(
                "💬 PREGUNTA PARA GEMINI: %s",
                pregunta_audio,
            )

            await responder_con_gemini(
                update,
                context,
                pregunta_audio,
                por_voz=True,
            )
            return

        # 4. Conversación normal por escrito.
        logger.info(
            "💬 MODO GEMINI (TEXTO)"
        )

        await responder_con_gemini(
            update,
            context,
            texto,
            por_voz=False,
        )

    except Exception:
        logger.exception(
            "❌ Error al procesar mensaje."
        )

        try:
            await update.message.reply_text(
                "💜 Ups, tuve un problema "
                "al procesar tu mensaje."
            )
        except TelegramError:
            pass




# ============================================================
# ERRORES GENERALES
# ============================================================

async def manejar_error(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.error(
        "Error no controlado en LightBy",
        exc_info=context.error,
    )


# ============================================================
# INICIALIZACIÓN
# ============================================================

def main():
    if not TOKEN:
        print("❌ ERROR: TELEGRAM_TOKEN no configurado.")
        print("📌 Revisa tu archivo .env.")
        raise SystemExit(1)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🤖 Iniciando LightBy AI...")
    print("💜 Personalidad de LightBy activada")
    print("💬 Conversación con Gemini disponible")
    print("🧠 Machine Learning disponible")
    print("👁️ Visión artificial disponible")
    print("🎧 Reconocimiento de voz disponible")
    print("🎙️ Ximena configurada mediante Cartesia")
    print("🔁 Repetición de respuestas disponible")
    print("📝 Recuperación de respuestas disponible")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", bienvenida)
    )

    app.add_handler(
        CommandHandler("ayuda", ayuda)
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            recibir_imagen,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.VOICE | filters.AUDIO,
            recibir_audio,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            responder,
        )
    )

    app.add_error_handler(manejar_error)

    print("🟢 LightBy está activa. Esperando mensajes...")

    app.run_polling(
        drop_pending_updates=False,
    )


if __name__ == "__main__":
    main()
