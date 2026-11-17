
import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def buscar_en_internet(consulta):
    """
    Busca información en internet utilizando Tavily.
    Devuelve resultados con título, contenido y fuente.
    """

    if not TAVILY_API_KEY:
        print("❌ No se encontró la clave de Tavily.")
        return []

    consulta = (consulta or "").strip()

    if not consulta:
        return []

    try:
        cliente = TavilyClient(api_key=TAVILY_API_KEY)

        print(f"🌐 Lumi está buscando: {consulta}")

        respuesta = cliente.search(
            query=consulta,
            search_depth="basic",
            max_results=3,
            include_answer=False,
            include_raw_content=False,
        )

        resultados = []

        for resultado in respuesta.get("results", []):
            resultados.append({
                "titulo": resultado.get("title", ""),
                "contenido": resultado.get("content", ""),
                "url": resultado.get("url", ""),
            })

        print(
            f"✅ Lumi encontró {len(resultados)} resultados."
        )

        return resultados

    except Exception as error:
        print(f"❌ Error en la búsqueda: {type(error).__name__}")
        print(f"Detalle: {error}")
        return []


if __name__ == "__main__":
    print("🤖💜 Probando el buscador de Lumi...")

    resultados = buscar_en_internet(
        "¿Qué es Python y para qué se utiliza?"
    )

    for numero, resultado in enumerate(resultados, start=1):
        print(f"\n📌 Resultado {numero}")
        print(f"Título: {resultado['titulo']}")
        print(f"Contenido: {resultado['contenido']}")
        print(f"Fuente: {resultado['url']}")
