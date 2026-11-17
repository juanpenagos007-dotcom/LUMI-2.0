
import re
import unicodedata


def normalizar_musica(texto):
    """
    Normaliza texto sin depender de mayúsculas ni tildes.
    """
    texto = unicodedata.normalize(
        "NFD",
        str(texto or "").lower(),
    )

    return "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )


def extraer_peticion_musica(texto):
    """
    Detecta solicitudes explícitas de música.

    Devuelve:
        str: canción, artista o búsqueda solicitada.
        "": solicitud musical sin datos suficientes.
        None: no se detectó una solicitud musical.
    """
    original = str(texto or "").strip()

    if not original:
        return None

    normalizado = normalizar_musica(original)

    prefijo = (
        r"^\s*"
        r"(?:(?:hola|oye|hey)[,!.\s]+)?"
        r"(?:(?:lumi|lightby|light by)[,!.\s]+)?"
        r"(?:(?:por favor)[,!.\s]+)?"
    )

    acciones = (
        r"(?:"
        r"ponme|pon|ponernos|"
        r"reproduce|reproduceme|reproducir|"
        r"quiero escuchar|quisiera escuchar|"
        r"me gustaria escuchar|"
        r"dejame escuchar|"
        r"quiero oir|dejame oir|"
        r"buscame|busca|"
        r"encuentrame|encuentra"
        r")"
    )

    patron = re.compile(
        prefijo + acciones + r"\b\s*(.*)$",
        re.IGNORECASE,
    )

    coincidencia = patron.match(normalizado)

    if coincidencia is None:
        return None

    solicitud = original[
        coincidencia.start(1):
    ].strip()

    solicitud_normalizada = normalizar_musica(
        solicitud
    )

    accion = normalizado[
        coincidencia.start():
        coincidencia.start(1)
    ]

    es_busqueda = bool(
        re.search(
            r"\b(?:buscame|busca|"
            r"encuentrame|encuentra)\b",
            accion,
        )
    )

    if es_busqueda:
        if re.match(
            r"^(?:en internet|en la web|"
            r"informacion|noticias|"
            r"que|como|cuando|donde|por que)\b",
            solicitud_normalizada,
        ):
            return None

        if not re.search(
            r"\b(?:cancion|canciones|tema|"
            r"musica|video musical|videoclip|"
            r"youtube|artista|album|disco)\b",
            solicitud_normalizada,
        ):
            return None

    solicitud = re.sub(
        r"^(?:(?:una|un|la|el)\s+)?"
        r"(?:canción|cancion|canciones|"
        r"tema|música|musica|"
        r"video musical|videoclip)"
        r"(?:\s+(?:de|del|llamada|llamado))?\s*",
        "",
        solicitud,
        flags=re.IGNORECASE,
    ).strip()

    solicitud = re.sub(
        r"^algo\s+de\s+",
        "",
        solicitud,
        flags=re.IGNORECASE,
    ).strip()

    solicitud = re.sub(
        r"\s+en\s+youtube\s*$",
        "",
        solicitud,
        flags=re.IGNORECASE,
    ).strip()

    return solicitud.strip(" ,.!?¿¡")


def extraer_correccion_musica(texto):
    """
    Detecta correcciones sobre una canción anterior.

    Ejemplos:
        "Esa no es, es la de Ram Jam"
        "Es la de Ram Jam"
        "Era la de Tchaikovsky"
        "No, era la de Queen"
        "Me refería a la de Spiderbait"

    Devuelve la corrección o None.

    IMPORTANTE:
    Debe utilizarse únicamente cuando exista
    contexto de una búsqueda musical anterior.
    """
    original = str(texto or "").strip()

    if not original:
        return None

    normalizado = normalizar_musica(original)

    patrones = [
        (
            r"^(?:esa|esta|ese|este)\s+no\s+es"
            r"(?:\s+la\s+cancion)?"
            r"\s*[,;:.!?-]*\s*"
            r"(?:(?:es|era|quiero|busco)\s+)?"
            r"(.+)$"
        ),
        (
            r"^no\s*[,;:.!?-]*\s*"
            r"(?:es|era|quiero|busco)\s+(.+)$"
        ),
        (
            r"^(?:es|era)\s+"
            r"(?:la|el)\s+de\s+(.+)$"
        ),
        (
            r"^(?:es|era)\s+"
            r"(?:la|el)\s+(.+)$"
        ),
        (
            r"^(?:me\s+referia\s+a|"
            r"me\s+refiero\s+a|"
            r"quise\s+decir)\s+(.+)$"
        ),
        (
            r"^(?:la\s+correcta\s+es|"
            r"la\s+que\s+quiero\s+es)\s+(.+)$"
        ),
    ]

    for patron in patrones:
        coincidencia = re.match(
            patron,
            normalizado,
            re.IGNORECASE,
        )

        if coincidencia is None:
            continue

        correccion = original[
            coincidencia.start(1):
        ].strip(" ,.!?¿¡")

        if correccion:
            return correccion

    return None


def limpiar_correccion_musical(correccion):
    """
    Elimina expresiones introductorias para
    obtener el artista o versión solicitada.
    """
    texto = str(correccion or "").strip()

    patrones = [
        r"^(?:es|era|quiero|busco)\s+",
        r"^(?:(?:la|el)\s+)?"
        r"(?:canción|cancion|versión|version|tema)"
        r"\s+",
        r"^(?:la|el)\s+de\s+",
        r"^de\s+",
        r"^(?:la|el)\s+",
    ]

    for patron in patrones:
        texto = re.sub(
            patron,
            "",
            texto,
            flags=re.IGNORECASE,
        ).strip()

    return texto.strip(" ,.!?¿¡")


def construir_consulta_corregida(
    consulta_anterior,
    correccion,
    titulo_anterior=None,
    artista_anterior=None,
):
    """
    Construye una nueva búsqueda utilizando
    el contexto musical anterior.

    Si se conoce el título encontrado, conserva
    ese título y reemplaza el artista.

    Ejemplos:
        Black Betty / Spiderbait + Ram Jam
        -> Black Betty Ram Jam

        Swan Lake + Tchaikovsky
        -> Swan Lake Tchaikovsky
    """
    anterior = str(
        consulta_anterior or ""
    ).strip()

    nueva = limpiar_correccion_musical(
        correccion
    )

    titulo = str(
        titulo_anterior or ""
    ).strip()

    artista = str(
        artista_anterior or ""
    ).strip()

    if not nueva:
        return anterior

    if not anterior and not titulo:
        return nueva

    nueva_normalizada = normalizar_musica(nueva)

    # Si la corrección contiene un nuevo título
    # explícito, utilizarlo directamente.
    if re.search(
        r"\b(?:cancion|tema|titulo)\s+",
        normalizar_musica(correccion),
    ):
        return nueva

    # Caso preferido: conocemos el título exacto
    # de la canción anterior.
    if titulo:
        if nueva_normalizada == normalizar_musica(
            artista
        ):
            return f"{titulo} {artista}".strip()

        if nueva_normalizada in normalizar_musica(
            titulo
        ):
            return nueva

        return f"{titulo} {nueva}".strip()

    # Si no hay título del catálogo, intentamos
    # quitar el artista anterior de la consulta.
    if artista and anterior:
        patron_artista = re.compile(
            r"\s+(?:de\s+)?"
            + re.escape(artista)
            + r"\s*$",
            re.IGNORECASE,
        )

        anterior = patron_artista.sub(
            "",
            anterior,
        ).strip()

    if nueva_normalizada in normalizar_musica(
        anterior
    ):
        return anterior

    return f"{anterior} {nueva}".strip()


def es_confirmacion_musical(texto):
    """
    Reconoce confirmaciones breves, con o sin
    tildes, mayúsculas y signos de puntuación.
    """
    limpio = normalizar_musica(texto)
    limpio = re.sub(r"[^\w\s]", " ", limpio)
    limpio = " ".join(limpio.split())

    return limpio in {
        "si",
        "si por favor",
        "si porfa",
        "si por fa",
        "si porfis",
        "claro",
        "claro que si",
        "dale",
        "hazlo",
        "buscala",
        "buscalo",
        "por favor",
    }


def es_cancelacion_musical(texto):
    """
    Reconoce respuestas negativas o cancelaciones.
    """
    limpio = normalizar_musica(texto).strip(
        " ¿?¡!.,"
    )

    return limpio in {
        "no",
        "no gracias",
        "cancelar",
        "cancela",
        "olvidalo",
        "mejor no",
        "dejalo",
    }


if __name__ == "__main__":
    ejemplos = [
        "Lumi, ponme Billie Jean de Michael Jackson",
        "Quiero escuchar Take On Me de a-ha",
        "Reproduce Bohemian Rhapsody",
        "Pon música de Queen",
        "Lumi, ponme una canción",
        "Lumi búscame la canción Swan Lake",
        "Búscame la canción Black Betty de Spiderbait",
        "Busca en internet qué es la música clásica",
        "¿Qué es la música clásica?",
    ]

    for ejemplo in ejemplos:
        print(
            f"\nMensaje: {ejemplo}"
        )
        print(
            "Detectado:",
            repr(extraer_peticion_musica(ejemplo)),
        )

    pruebas_correccion = [
        (
            "Black Betty de Spiderbait",
            "Black Betty",
            "Spiderbait",
            "Es la de Ram Jam",
        ),
        (
            "Swan Lake",
            "Swan Lake",
            "",
            "Esa no es, es la Tchaikovsky",
        ),
    ]

    for consulta, titulo, artista, mensaje in pruebas_correccion:
        correccion = extraer_correccion_musica(
            mensaje
        )

        resultado = construir_consulta_corregida(
            consulta,
            correccion,
            titulo_anterior=titulo,
            artista_anterior=artista,
        )

        print(f"\nCorrección: {mensaje}")
        print(f"Nueva búsqueda: {resultado}")

    print(
        "\nConfirmación:",
        es_confirmacion_musical("Sí por fa"),
    )
