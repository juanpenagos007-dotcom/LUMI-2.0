
"""
Lumi AI - Machine Learning híbrido.

Modelos preentrenados:
- Emociones: pysentimiento
- Lenguaje de odio: pysentimiento

Reglas propias:
- Intenciones
- Negaciones y correcciones contextuales
- Riesgo orientativo
- Señales de desinterés

Interfaz compatible con bot.py:
analizar_texto(texto) devuelve:
(emocion, toxicidad, ghosting, riesgo, intencion, confianza)

confianza = 0 significa "Ajuste contextual".
No representa una probabilidad del 0 %.
"""

import re
import unicodedata
from functools import lru_cache

from pysentimiento import create_analyzer


EMOCIONES = {
    "joy": "alegria",
    "sadness": "tristeza",
    "anger": "enojo",
    "fear": "miedo",
    "surprise": "sorpresa",
    "disgust": "disgusto",
    "neutral": "neutral",
}


def normalizar(texto):
    texto = unicodedata.normalize("NFD", str(texto).lower())
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", texto).strip()


def partes(texto):
    return [
        p.strip()
        for p in re.split(
            r"[,;.!?\n]+|\bpero\b|\bsino\b",
            normalizar(texto),
        )
        if p.strip()
    ]


def negado(fragmento, inicio):
    anterior = fragmento[max(0, inicio - 45):inicio]

    return bool(re.search(
        r"\b(?:no|nunca|jamas|tampoco|ni)\s+"
        r"(?:(?:me|te|se|lo|la|estoy|siento|"
        r"quiero|gusta|da|muy|tan)\s+){0,4}$",
        anterior,
    ))


EXPRESIONES_EMOCION = {
    "alegria": [
        r"\b(?:estoy|me siento|ando)\s+(?:muy\s+)?"
        r"(?:feliz|content[oa]|alegre|emocionad[oa]|orgullos[oa])\b",
        r"\b(?:que alegria|me alegra|lo logre|"
        r"lo consegui|que felicidad)\b",
    ],
    "tristeza": [
        r"\b(?:estoy|me siento|ando)\s+(?:muy\s+)?"
        r"(?:triste|desanimad[oa]|decaid[oa]|desilusionad[oa])\b",
        r"\b(?:tengo ganas de llorar|me siento sol[oa])\b",
    ],
    "enojo": [
        r"\b(?:estoy|me siento|ando)\s+(?:muy\s+)?"
        r"(?:enojad[oa]|furios[oa]|molest[oa]|indignad[oa]|brav[oa])\b",
        r"\b(?:me da (?:mucha\s+)?rabia|me enfurece|"
        r"estoy hart[oa]|me molesta muchisimo)\b",
    ],
    "miedo": [
        r"\b(?:estoy|me siento)\s+(?:muy\s+)?"
        r"(?:asustad[oa]|atemorizad[oa]|aterrad[oa])\b",
        r"\b(?:tengo miedo|me da miedo|me asusta|temo que)\b",
    ],
    "sorpresa": [
        r"\b(?:estoy|me quede)\s+(?:muy\s+)?"
        r"(?:sorprendid[oa]|impactad[oa])\b",
        r"\b(?:que sorpresa|no me lo esperaba|me sorprendio)\b",
    ],
    "disgusto": [
        r"\b(?:me da asco|que asco|me repugna|"
        r"me resulta desagradable|estoy asquead[oa])\b",
    ],
}


REGLAS = {
    "celebracion": {
        "fuertes": [
            r"\b(?:lo logre|lo consegui|lo logramos|"
            r"felicidades|felicitaciones|enhorabuena)\b",
            r"\b(?:estoy|me siento)\s+(?:muy\s+)?"
            r"(?:feliz|content[oa]|orgullos[oa])\b",
            r"\b(?:aprobe|gane|triunfe|que alegria|"
            r"buenas noticias)\b",
            r"\b(?:recibi|me dieron|tengo)\s+"
            r"(?:una\s+)?(?:noticia|noticias)\s+"
            r"(?:maravillosa|maravillosas|excelente|"
            r"excelentes|increible|increibles|buena|buenas)\b",
        ],
        "secundarias": [
            r"\b(?:termine|complete|consegui|alcance|logre)\b",
            r"\b(?:proyecto|tarea|meta|objetivo|examen|curso)\b",
            r"\b(?:excelente|genial|maravillos[oa])\b",
        ],
    },
    "agradecimiento": {
        "fuertes": [
            r"\b(?:gracias|muchas gracias|mil gracias|"
            r"te agradezco|te lo agradezco|"
            r"estoy agradecid[oa])\b",
        ],
        "secundarias": [
            r"\b(?:gratitud|agradecimiento|"
            r"valoro tu ayuda|aprecio tu ayuda)\b",
        ],
    },
    "reclamo": {
        "fuertes": [
            r"\b(?:nunca|jamas)\s+(?:me\s+)?"
            r"(?:escuchas|respondes|contestas|ayudas)\b",
            r"\b(?:no me (?:escuchas|respondes|"
            r"contestas|entiendes)|me ignoras|"
            r"ignoras mis|ignores mis)\b",
            r"\b(?:no respetas|no respeten|"
            r"no tienes en cuenta|estoy hart[oa] de|"
            r"me molesta que)\b",
        ],
        "secundarias": [
            r"\b(?:nunca|siempre|otra vez)\b",
            r"\b(?:molest[oa]|frustrad[oa]|injusticia)\b",
            r"\b(?:escuchar|ignorar|respetar|"
            r"opinion|opiniones)\b",
        ],
    },
    "celos": {
        "fuertes": [
            r"\b(?:con quien (?:estabas|saliste|hablabas)|"
            r"quien te (?:escribio|llamo|habla))\b",
            r"\b(?:te vi con (?:otr[oa]|alguien)|"
            r"me estas enganando)\b",
        ],
        "secundarias": [
            r"\b(?:celos|celos[oa]|infidelidad|"
            r"desconfio|sospecho|tu ex)\b",
        ],
    },
    "manipulacion": {
        "fuertes": [
            r"\b(?:si (?:realmente )?me quisieras|"
            r"si me amaras|es tu culpa que)\b",
            r"\bsi no .{1,45} entonces .{1,45}\b",
        ],
        "secundarias": [
            r"\b(?:chantaje|culpable|"
            r"tienes que demostrar|si de verdad me)\b",
        ],
    },
    "control": {
        "fuertes": [
            r"\b(?:mandame|enviame|comparte)\s+"
            r"(?:tu\s+)?ubicacion\b",
            r"\b(?:tienes que decirme donde estas|"
            r"dame tu contrasena|no puedes hablar con|"
            r"te prohibo)\b",
        ],
        "secundarias": [
            r"\b(?:vigilar|controlar|prohibir|"
            r"ubicacion|contrasena)\b",
        ],
    },
    "ruptura": {
        "fuertes": [
            r"\b(?:quiero|voy a|decidi)\s+terminar\s+"
            r"(?:contigo|la relacion|lo nuestro)\b",
            r"\b(?:no quiero seguir (?:contigo|"
            r"en esta relacion)|quiero dejarte|"
            r"tenemos que separarnos)\b",
            r"\b(?:lo nuestro se acabo|"
            r"ya no somos pareja)\b",
        ],
        "secundarias": [
            r"\b(?:separarnos|separacion|romper|"
            r"pareja|noviazgo|relacion)\b",
        ],
    },
    "agresion": {
        "fuertes": [
            r"\b(?:te odio|los odio|las odio|"
            r"que asco me das|callate|largate)\b",
            r"\beres un[ao]?\s+"
            r"(?:idiota|imbecil|estupid[oa])\b",
        ],
        "secundarias": [
            r"\b(?:idiota|imbecil|estupid[oa]|"
            r"insultar|humillar|despreciar)\b",
        ],
    },
    "afecto": {
        "fuertes": [
            r"\b(?:te (?:quiero|amo|adoro|extrano)|"
            r"me gustas|me encantas|"
            r"eres muy importante para mi)\b",
        ],
        "secundarias": [
            r"\b(?:carino|ternura|afecto|"
            r"te aprecio|te necesito)\b",
        ],
    },
    "tristeza": {
        "fuertes": [
            r"\b(?:estoy|me siento)\s+(?:muy\s+)?"
            r"(?:triste|desanimad[oa]|decaid[oa])\b",
            r"\b(?:tengo ganas de llorar|me siento sol[oa]|"
            r"me siento mal|estoy desilusionad[oa])\b",
        ],
        "secundarias": [
            r"\b(?:tristeza|soledad|llanto|"
            r"desanimad[oa]|desilusionad[oa])\b",
        ],
    },
    "desinteres": {
        "fuertes": [
            r"\b(?:no me interesa|me da igual|"
            r"no quiero hablar|dejame en paz|"
            r"no tengo ganas de hablar|"
            r"no quiero seguir conversando)\b",
        ],
        "secundarias": [
            r"\b(?:indiferente|desinteres|"
            r"como digas|no importa)\b",
        ],
    },
    "curiosidad": {
        "fuertes": [
            r"\b(?:quiero saber|me gustaria saber|"
            r"me puedes explicar|puedes explicarme|"
            r"tengo una pregunta|tengo una duda|"
            r"que significa|como funciona)\b",
        ],
        "secundarias": [
            r"\b(?:pregunta|duda|explicacion|"
            r"que|como|cuando|donde|quien|"
            r"cual|por que)\b",
        ],
    },
    "saludo": {
        "fuertes": [
            r"^(?:hola|holi|hey|buenas)\b",
            r"^(?:buenos dias|buenas tardes|"
            r"buenas noches)\b",
        ],
        "secundarias": [
            r"\b(?:saludos|bienvenid[oa])\b",
        ],
    },
    "despedida": {
        "fuertes": [
            r"\b(?:adios|hasta luego|hasta manana|"
            r"nos vemos|me despido)\b",
            r"^(?:chao|chau|bye)\b",
        ],
        "secundarias": [
            r"\b(?:hasta pronto|despedida)\b",
        ],
    },
}

PRIORIDAD = list(REGLAS)


def evidencia_emocional(texto):
    scores = {
        emocion: 0
        for emocion in EXPRESIONES_EMOCION
    }

    for fragmento in partes(texto):
        for emocion, patrones in EXPRESIONES_EMOCION.items():
            for patron in patrones:
                for match in re.finditer(patron, fragmento):
                    if not negado(fragmento, match.start()):
                        scores[emocion] += 1

    return scores


def detectar_intencion(texto):
    puntuaciones = {
        nombre: 0
        for nombre in REGLAS
    }

    fragmentos = partes(texto)
    texto_normalizado = normalizar(texto)

    for fragmento in fragmentos:
        for nombre, reglas in REGLAS.items():
            for patron in reglas["fuertes"]:
                for match in re.finditer(patron, fragmento):
                    if not negado(fragmento, match.start()):
                        puntuaciones[nombre] += 4

            for patron in reglas["secundarias"]:
                for match in re.finditer(patron, fragmento):
                    if not negado(fragmento, match.start()):
                        puntuaciones[nombre] += 1

    if puntuaciones["curiosidad"] < 4:
        puntuaciones["curiosidad"] = min(
            puntuaciones["curiosidad"], 1
        )

    # Terminar un proyecto no significa terminar una relación.
    if re.search(
        r"\b(?:proyecto|tarea|examen|curso|objetivo)\b",
        texto_normalizado,
    ):
        if not re.search(
            r"\b(?:terminar contigo|terminar la relacion|"
            r"quiero dejarte)\b",
            texto_normalizado,
        ):
            puntuaciones["ruptura"] = 0

        if re.search(
            r"\b(?:termine|complete|logre|consegui)\b",
            texto_normalizado,
        ):
            puntuaciones["celebracion"] += 2

    # Una ruptura requiere evidencia directa y no negada.
    ruptura_confirmada = False

    for fragmento in fragmentos:
        for patron in REGLAS["ruptura"]["fuertes"]:
            for match in re.finditer(patron, fragmento):
                if not negado(fragmento, match.start()):
                    ruptura_confirmada = True

    if not ruptura_confirmada:
        puntuaciones["ruptura"] = 0

    # Los saludos no deben dominar mensajes extensos.
    if len(texto_normalizado.split()) > 12:
        puntuaciones["saludo"] = min(
            puntuaciones["saludo"], 1
        )
        puntuaciones["despedida"] = min(
            puntuaciones["despedida"], 1
        )

    mejor = max(
        PRIORIDAD,
        key=lambda nombre: (
            puntuaciones[nombre],
            -PRIORIDAD.index(nombre),
        ),
    )

    return mejor if puntuaciones[mejor] >= 3 else "normal"


# Correcciones conservadoras de negación.
# No intentamos deducir la emoción real de una persona.
NEGACIONES_EMOCION = {
    "alegria": [
        r"\b(?:no|nunca|jamas)\s+(?:estoy|me siento|ando)\s+"
        r"(?:muy\s+)?(?:feliz|content[oa]|alegre|emocionad[oa])\b",
    ],
    "tristeza": [
        r"\b(?:no|nunca|jamas)\s+(?:estoy|me siento|ando)\s+"
        r"(?:muy\s+)?(?:triste|desanimad[oa]|decaid[oa])\b",
    ],
    "enojo": [
        r"\b(?:no|nunca|jamas)\s+(?:estoy|me siento|ando)\s+"
        r"(?:muy\s+)?(?:enojad[oa]|furios[oa]|molest[oa])\b",
    ],
    "miedo": [
        r"\b(?:no|nunca|jamas)\s+(?:estoy|me siento)\s+"
        r"(?:muy\s+)?(?:asustad[oa]|atemorizad[oa])\b",
        r"\b(?:no|nunca|jamas)\s+tengo miedo\b",
    ],
    "sorpresa": [
        r"\b(?:no|nunca|jamas)\s+(?:estoy|me quede)\s+"
        r"(?:muy\s+)?(?:sorprendid[oa]|impactad[oa])\b",
    ],
    "disgusto": [
        r"\b(?:no|nunca|jamas)\s+me da asco\b",
    ],
}


def emociones_negadas(texto):
    resultado = set()
    texto_normalizado = normalizar(texto)

    for emocion, patrones in NEGACIONES_EMOCION.items():
        if any(
            re.search(patron, texto_normalizado)
            for patron in patrones
        ):
            resultado.add(emocion)

    return resultado


def detectar_emocion_hibrida(texto, prediccion):
    """
    Prioriza evidencia emocional explícita no negada.
    Conserva la confianza del ML solamente cuando
    se utiliza su predicción sin modificarla.
    """
    raw = str(prediccion.output).lower()
    emocion_ml = EMOCIONES.get(raw, "neutral")

    probas = getattr(prediccion, "probas", {}) or {}
    confianza_ml = float(
        probas.get(
            prediccion.output,
            max(probas.values(), default=0),
        )
    )
    confianza_ml = round(
        max(0, min(confianza_ml, 1)) * 100
    )

    senales = evidencia_emocional(texto)
    negadas = emociones_negadas(texto)

    ordenadas = sorted(
        senales.items(),
        key=lambda par: par[1],
        reverse=True,
    )

    # Una emoción explícita afirmada puede corregir al modelo.
    if ordenadas and ordenadas[0][1] > 0:
        mejor, cantidad = ordenadas[0]

        empate = (
            len(ordenadas) > 1
            and ordenadas[1][1] == cantidad
        )

        if not empate:
            if mejor != emocion_ml:
                return mejor, 0

            return emocion_ml, confianza_ml

    # Si el modelo afirma una emoción que el texto niega,
    # evitamos repetirla como una certeza.
    if emocion_ml in negadas:
        return "neutral", 0

    return emocion_ml, confianza_ml


def calcular_ghosting(texto, intencion, emocion=None):
    """
    Heurística de desinterés o evasión.
    No es una probabilidad real de ghosting.
    """
    if intencion != "desinteres":
        return 0

    score = 20
    texto = normalizar(texto)

    if len(texto.split()) <= 3:
        score += 15

    if re.search(
        r"\b(?:no quiero hablar|me da igual|"
        r"no me interesa)\b",
        texto,
    ):
        score += 15

    return min(score, 50)


@lru_cache(maxsize=1)
def modelos():
    print("🔄 Cargando modelos de Lumi AI...")

    emociones = create_analyzer(
        task="emotion",
        lang="es",
    )

    odio = create_analyzer(
        task="hate_speech",
        lang="es",
    )

    print("✅ Modelos cargados correctamente")

    return emociones, odio


def analizar_texto(texto):
    """
    Devuelve exactamente seis resultados para bot.py.
    """
    if not texto or not str(texto).strip():
        return "neutral", "no", 0, "🟢 Bajo", "normal", 0

    texto = str(texto).strip()

    emociones, odio = modelos()

    # Predicciones reales de los modelos.
    pred_emocion = emociones.predict(texto)
    pred_odio = odio.predict(texto)

    # Sistema híbrido: ML + reglas contextuales.
    emocion, confianza = detectar_emocion_hibrida(
        texto,
        pred_emocion,
    )

    intencion = detectar_intencion(texto)

    probas_odio = {
        str(k).lower(): float(v)
        for k, v in (
            getattr(pred_odio, "probas", {}) or {}
        ).items()
    }

    hateful = probas_odio.get("hateful", 0)
    targeted = probas_odio.get("targeted", 0)

    toxicidad = (
        "si"
        if max(hateful, targeted) >= 0.5
        else "no"
    )

    if max(hateful, targeted) >= 0.7:
        riesgo = "🔴 Alto"

    elif (
        intencion in {
            "agresion",
            "control",
            "manipulacion",
        }
        or (
            intencion == "reclamo"
            and emocion in {"enojo", "disgusto"}
        )
    ):
        riesgo = "🟡 Medio"

    else:
        riesgo = "🟢 Bajo"

    ghosting = calcular_ghosting(
        texto,
        intencion,
        emocion,
    )

    return (
        emocion,
        toxicidad,
        ghosting,
        riesgo,
        intencion,
        confianza,
    )


# Pruebas de intención: se conservan las 26 originales.
PRUEBAS = [
    ("Estoy feliz porque terminé mi proyecto.", "celebracion"),
    ("Me siento triste y desanimado.", "tristeza"),
    ("Estoy muy enojado porque nunca me escuchas.", "reclamo"),
    ("Gracias por ayudarme con la tarea.", "agradecimiento"),
    ("Te quiero mucho.", "afecto"),
    ("Quiero terminar contigo.", "ruptura"),
    ("¿Cómo funciona este programa?", "curiosidad"),
    ("Hola, buenos días.", "saludo"),
    ("Nos vemos mañana, chao.", "despedida"),
    ("No quiero hablar ahora.", "desinteres"),
    ("¡Qué sorpresa tan increíble!", "normal"),
    ("Me siento asustado por el examen.", "normal"),
    ("Hoy compré un cuaderno.", "normal"),
    ("Estoy furioso, me da mucha rabia lo que pasó.", "normal"),
    ("Me molesta muchísimo que no respeten mis opiniones.", "reclamo"),
    ("Estoy enojado porque las cosas no salieron bien.", "normal"),
    ("No estoy triste, estoy enojado.", "normal"),
    ("Terminé mi tarea, no mi relación.", "celebracion"),
    ("Estoy sorprendido por la noticia.", "normal"),
    ("Me da asco ese olor.", "normal"),
    ("No estoy triste.", "normal"),
    ("No te odio, estoy molesto.", "normal"),
    ("No quiero terminar contigo.", "normal"),
    ("No estoy feliz por lo que pasó.", "normal"),
    ("Estoy triste, pero agradecido por tu ayuda.", "tristeza"),
    ("¿Por qué nunca me escuchas?", "reclamo"),
    ("Hoy recibí una noticia maravillosa.", "celebracion"),
]


# Pruebas nuevas de emoción.
# Son ejemplos orientativos, no un conjunto de evaluación
# independiente para medir la precisión general.
PRUEBAS_EMOCION = [
    ("Estoy muy feliz.", "alegria"),
    ("Me siento triste.", "tristeza"),
    ("Estoy enojado.", "enojo"),
    ("Tengo miedo.", "miedo"),
    ("Estoy sorprendido.", "sorpresa"),
    ("Me da asco ese olor.", "disgusto"),
    ("No estoy triste.", "neutral"),
    ("No estoy triste, estoy enojado.", "enojo"),
    ("No estoy feliz.", "neutral"),
    ("Estoy triste, pero agradecido por tu ayuda.", "tristeza"),
    ("Hoy compré un cuaderno.", "neutral"),
]


def validar_patrones():
    for patrones in EXPRESIONES_EMOCION.values():
        for patron in patrones:
            re.compile(patron)

    for patrones in NEGACIONES_EMOCION.values():
        for patron in patrones:
            re.compile(patron)

    for grupos in REGLAS.values():
        for patron in (
            grupos["fuertes"] + grupos["secundarias"]
        ):
            re.compile(patron)

    print("✅ Todas las expresiones regulares son válidas.")


def ejecutar_pruebas():
    validar_patrones()

    aprobadas_intencion = 0
    aprobadas_emocion = 0

    print("\n🧪 PRUEBAS DE INTENCIONES\n")

    for i, (mensaje, esperado) in enumerate(PRUEBAS, 1):
        try:
            resultado = analizar_texto(mensaje)
            emocion, _, _, _, intencion, confianza = resultado

            ok = intencion == esperado
            aprobadas_intencion += int(ok)

            print(
                f"{'✅' if ok else '❌'} {i:02d} | {mensaje}"
            )
            print(
                f"    Emoción: {emocion} | "
                f"Intención: {intencion} | "
                f"Esperada: {esperado}"
            )
            print(
                "    Confianza: "
                + (
                    "Ajuste contextual"
                    if confianza == 0
                    else f"{confianza}%"
                )
            )

        except Exception as exc:
            print(
                f"❌ {i:02d} | ERROR: "
                f"{type(exc).__name__}: {exc}"
            )

    print("\n🧪 PRUEBAS DE EMOCIONES\n")

    for i, (mensaje, esperado) in enumerate(
        PRUEBAS_EMOCION, 1
    ):
        try:
            emocion, _, _, _, _, confianza = analizar_texto(
                mensaje
            )

            ok = emocion == esperado
            aprobadas_emocion += int(ok)

            print(
                f"{'✅' if ok else '❌'} {i:02d} | {mensaje}"
            )
            print(
                f"    Detectada: {emocion} | "
                f"Esperada: {esperado}"
            )
            print(
                "    Confianza: "
                + (
                    "Ajuste contextual"
                    if confianza == 0
                    else f"{confianza}%"
                )
            )

        except Exception as exc:
            print(
                f"❌ {i:02d} | ERROR: "
                f"{type(exc).__name__}: {exc}"
            )

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    print(
        f"📊 INTENCIONES: "
        f"{aprobadas_intencion}/{len(PRUEBAS)}"
    )

    print(
        f"📊 EMOCIONES: "
        f"{aprobadas_emocion}/{len(PRUEBAS_EMOCION)}"
    )

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    ejecutar_pruebas()
