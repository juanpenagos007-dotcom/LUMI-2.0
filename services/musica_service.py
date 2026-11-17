
import json
import os
import re
import urllib.parse
import urllib.request

from pathlib import Path


ITUNES_API = "https://itunes.apple.com/search"
YOUTUBE_API = "https://www.googleapis.com/youtube/v3/search"


def cargar_clave_youtube():
    """
    Obtiene la clave desde las variables de entorno.
    Si existe python-dotenv, también carga el .env
    ubicado en la raíz del proyecto.
    """
    try:
        from dotenv import load_dotenv

        raiz = Path(__file__).resolve().parent.parent
        load_dotenv(raiz / ".env")
    except ImportError:
        pass

    return os.getenv("YOUTUBE_API_KEY", "").strip()


def solicitar_json(url, timeout=12):
    solicitud = urllib.request.Request(
        url,
        headers={
            "User-Agent": "LumiBot/2.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(
        solicitud,
        timeout=timeout,
    ) as respuesta:
        return json.loads(
            respuesta.read().decode("utf-8")
        )


def buscar_video_youtube(titulo, artista):
    """
    Busca un video de YouTube usando su API oficial.

    No utiliza Gemini, Tavily ni Cartesia.

    Si no hay clave o falla la búsqueda,
    devuelve None.
    """
    clave = cargar_clave_youtube()

    if not clave:
        return None

    consulta = f"{titulo} {artista} official music video".strip()

    parametros = urllib.parse.urlencode({
        "part": "snippet",
        "q": consulta,
        "type": "video",
        "videoCategoryId": "10",
        "maxResults": 5,
        "key": clave,
    })

    url = f"{YOUTUBE_API}?{parametros}"

    try:
        datos = solicitar_json(url)

        resultados = datos.get("items", [])

        for video in resultados:
            video_id = video.get("id", {}).get("videoId")

            if video_id:
                return (
                    "https://www.youtube.com/watch?v="
                    + video_id
                )

    except Exception as error:
        print(
            "⚠️ No se pudo buscar el video en YouTube:",
            type(error).__name__,
            str(error),
        )

    return None


def enlace_busqueda_youtube(consulta):
    return (
        "https://www.youtube.com/results?search_query="
        + urllib.parse.quote_plus(consulta)
    )


def buscar_cancion(consulta):
    """
    Busca una canción utilizando la API pública
    de iTunes.

    Si hay una clave de YouTube configurada,
    también intenta obtener un enlace directo
    a un video.

    No utiliza créditos de Gemini, Tavily
    ni Cartesia.
    """
    consulta = str(consulta or "").strip()

    if not consulta:
        return None

    parametros = urllib.parse.urlencode({
        "term": consulta,
        "entity": "song",
        "media": "music",
        "limit": 5,
        "country": "US",
    })

    url = f"{ITUNES_API}?{parametros}"

    try:
        datos = solicitar_json(url)
        canciones = datos.get("results", [])

        if not canciones:
            return None

        cancion = canciones[0]

        titulo = cancion.get("trackName", "")
        artista = cancion.get("artistName", "")
        album = cancion.get("collectionName", "")
        fecha = cancion.get("releaseDate", "")
        duracion_ms = cancion.get("trackTimeMillis", 0)

        minutos, segundos = divmod(
            int(duracion_ms / 1000),
            60,
        )

        duracion = (
            f"{minutos}:{segundos:02d}"
            if duracion_ms
            else "No disponible"
        )

        busqueda = f"{titulo} {artista}".strip()

        enlace_directo = buscar_video_youtube(
            titulo,
            artista,
        )

        enlace_youtube = (
            enlace_directo
            or enlace_busqueda_youtube(busqueda)
        )

        enlace_spotify = (
            "https://open.spotify.com/search/"
            + urllib.parse.quote(busqueda, safe="")
        )

        return {
            "titulo": titulo,
            "artista": artista,
            "album": album,
            "fecha": fecha[:10] if fecha else "",
            "duracion": duracion,
            "portada": cancion.get("artworkUrl100", ""),
            "vista_previa": cancion.get("previewUrl", ""),
            "enlace_apple": cancion.get("trackViewUrl", ""),
            "enlace_youtube": enlace_youtube,
            "enlace_spotify": enlace_spotify,
            "youtube_directo": bool(enlace_directo),
        }

    except Exception as error:
        print(
            "❌ Error al buscar música:",
            type(error).__name__,
            str(error),
        )
        return None


def formatear_cancion(cancion):
    """
    Prepara la información para Telegram.
    """
    if not cancion:
        return (
            "💜 No encontré esa canción. "
            "¿Puedes decirme el título y el artista?"
        )

    youtube_directo = cancion.get(
        "youtube_directo",
        False,
    )

    descripcion_youtube = (
        "▶️ Ver video en YouTube:"
        if youtube_directo
        else "🔎 Buscar en YouTube:"
    )

    return (
        "🎶💜 ¡Encontré esta canción!\n\n"
        f"🎵 Título: {cancion['titulo']}\n"
        f"🎤 Artista: {cancion['artista']}\n"
        f"💿 Álbum: {cancion['album']}\n"
        f"📅 Fecha: {cancion['fecha']}\n"
        f"⏱️ Duración: {cancion['duracion']}\n\n"
        f"{descripcion_youtube}\n"
        f"{cancion['enlace_youtube']}\n\n"
        "🎧 Otras plataformas:\n"
        f"🟢 Spotify: {cancion['enlace_spotify']}\n"
        f"🍎 Apple: {cancion['enlace_apple']}\n\n"
        "💜 ¡Disfruta la música!"
    )


if __name__ == "__main__":
    print("🎶💜 Probando el buscador musical...")

    resultado = buscar_cancion(
        "Take On Me a-ha"
    )

    if resultado:
        print(formatear_cancion(resultado))

        print(
            "\nVista previa disponible:",
            bool(resultado["vista_previa"]),
        )

        print(
            "Video directo de YouTube:",
            resultado["youtube_directo"],
        )
    else:
        print("No se encontraron resultados.")
