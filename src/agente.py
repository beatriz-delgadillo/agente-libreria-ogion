import re

import pandas as pd

from base_de_datos import obtener_conexion, quitar_acentos

import ollama

# definir mensaje ollama
def hablar_con_ollama(mensaje):
    respuesta = ollama.chat(
        model="phi3",
        messages=[
            {
                "role": "system",
                "content": """
Eres Ogion, un asistente de biblioteca pública.

Reglas obligatorias:


1. Utiliza únicamente la información incluida en el contexto recuperado.
2. Nunca inventes información.
3. No deduzcas ni completes datos faltantes.
4. Si el contexto no contiene la respuesta, responde exactamente:
"No encontré información sobre eso en los registros de la biblioteca."
5. Responde de forma clara, breve y amable.
6. Tu prioridad absoluta es la precisión por encima de la creatividad.
""",
            },
            {
                "role": "user",
                "content": mensaje,
            },
        ],
         options={
            "temperature": 0,
        },
    )

    return respuesta["message"]["content"]

#Definicion de herramientas de busqueda 

# Límite de resultados por búsqueda
LIMITE_RESULTADOS = 10

# Palabras que no aportan a la búsqueda (conectores, preguntas genéricas).

PALABRAS_VACIAS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "en", "y", "o", "u", "que", "qué", "cual", "cuál", "cuales", "cuáles",
    "es", "son", "hay", "tiene", "tienen", "puedo", "puede", "pueden",
    "como", "cómo", "para", "por", "con", "sobre", "informacion",
    "información", "a", "se", "si", "sí", "existe", "existen",
}


def tokenizar_consulta(consulta):
    """Convierte una pregunta libre en una lista de palabras clave,
    quitando signos de puntuación y palabras vacías. Si tras filtrar
    no queda ninguna palabra útil, usa la consulta original tal cual."""
    limpio = re.sub(r"[¿?¡!.,;:]", " ", consulta.lower())
    palabras = [
        p for p in limpio.split() if p and p not in PALABRAS_VACIAS and len(p) > 2
    ]
    return palabras or [consulta.strip()]


def variantes_palabra(palabra):
    """Genera variantes simples de singular/plural de una palabra, para
    que buscar 'novelas' también encuentre filas que dicen 'Novela'
    (y viceversa). Es una regla simple, no cubre plurales irregulares,
    pero resuelve el caso más común en español (agregar/quitar 's')."""
    variantes = {palabra}
    if palabra.endswith("s") and len(palabra) > 4:
        variantes.add(palabra[:-1])
    else:
        variantes.add(palabra + "s")
    return variantes


def _buscar_generico(tabla, columnas, consulta):
    """Busca en `tabla` filas donde CUALQUIERA de las palabras clave de
    la consulta (o sus variantes de singular/plural) aparezca en
    CUALQUIERA de las columnas indicadas, ignorando acentos."""
    palabras = tokenizar_consulta(consulta)

    todas_las_variantes = set()
    for palabra in palabras:
        for variante in variantes_palabra(quitar_acentos(palabra)):
            todas_las_variantes.add(variante)

    condiciones = []
    parametros = []
    for variante in todas_las_variantes:
        patron = f"%{variante}%"
        sub_condicion = " OR ".join(
            f"quitar_acentos({columna}) LIKE ?" for columna in columnas
        )
        condiciones.append(f"({sub_condicion})")
        parametros.extend([patron] * len(columnas))

    query = f"""
        SELECT * FROM {tabla}
        WHERE {' OR '.join(condiciones)}
        LIMIT ?
    """
    parametros.append(LIMITE_RESULTADOS)

    conn = obtener_conexion()
    resultados = pd.read_sql_query(query, conn, params=parametros)
    conn.close()
    return resultados


def buscar_libros(consulta):
    return _buscar_generico("catalogo", ["titulo", "autor", "genero"], consulta)


def buscar_horarios(consulta):
    return _buscar_generico("horarios", ["dia"], consulta)


def buscar_eventos(consulta):
    return _buscar_generico(
        "eventos", ["nombre", "fecha", "descripcion", "publico"], consulta
    )


def buscar_faq(consulta):
    return _buscar_generico("faq", ["pregunta", "respuesta"], consulta)


def buscar_politicas(consulta):
    return _buscar_generico(
        "politicas", ["categoria", "pregunta", "respuesta"], consulta
    )

#Definicion de herramientas de respuesta con contexto


def formatear_contexto(df):
    """Convierte un DataFrame en bloques de texto tipo 'columna: valor',
    uno por fila, en vez de una tabla alineada con espacios (ambigua
    para modelos chicos)."""
    bloques = []
    for _, fila in df.iterrows():
        bloques.append("\n".join(f"{col}: {val}" for col, val in fila.items()))
    return "\n---\n".join(bloques)


# Verbos y conectores se ignoran para no rechazar respuestas correctas por falsos positivos.
PALABRAS_COMUNES_NO_VERIFICABLES = {
    "tenemos", "contamos", "hay", "existen", "existe", "también", "además",
    "actualmente", "cada", "toda", "todos", "todas", "puede", "pueden",
    "según", "cabe", "estos", "estas", "esto", "esta", "este", "otro", "otra",
    "otros", "otras", "sobre", "para", "esos", "esas", "aquí", "allí",
    "tienen", "tiene",
}


def verificar_fidelidad(respuesta, contexto):
    """Revisa que los datos concretos (números, nombres propios) que
    aparecen en la respuesta del modelo también existan en el contexto
    recuperado. Si algo no aparece, es señal de posible alucinación.

    Tolera reformulaciones comunes de rangos numéricos, por ejemplo
    que el modelo escriba "3-7" cuando el contexto original dice
    "3 a 7", ya que es una paráfrasis válida y no un dato inventado.
    También ignora verbos/conectores comunes que aparecen capitalizados
    solo por estar al inicio de una oración (no son datos reales).
    """
    tokens = re.findall(
        r'\b\d{1,4}(?:-\d+)*\b|\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,}\b', respuesta
    )

    faltantes = []
    for t in tokens:
        if t.lower() in PALABRAS_COMUNES_NO_VERIFICABLES:
            continue

        if t in contexto:
            continue

        rango = re.match(r'^(\d+)-(\d+)$', t)
        if rango and f"{rango.group(1)} a {rango.group(2)}" in contexto:
            continue

        faltantes.append(t)

    return faltantes


def responder_con_contexto(pregunta, resultados, mensaje_sin_resultados):
    if resultados.empty:
        return mensaje_sin_resultados
    else:
        contexto = formatear_contexto(resultados)

    mensaje = f"""
Contexto recuperado:
{contexto}

Pregunta del usuario:
{pregunta}

Instrucciones obligatorias:


1. Responde únicamente con información escrita de forma literal en el contexto.
2. No agregues lugares, áreas, procedimientos, pasos ni recomendaciones que no aparezcan en el contexto.
3. No reformules una ausencia de información como una explicación probable.
4. Si el contexto no contiene la respuesta exacta, responde exactamente:
"No encontré información sobre eso en los registros de la biblioteca."
5. Puedes resumir, pero no añadir ningún dato nuevo.
6. Sé breve y directo.

Respuesta:
"""

    respuesta_final = hablar_con_ollama(mensaje)

    faltantes = verificar_fidelidad(respuesta_final, contexto)
    if faltantes:
        return "No encontré información confiable sobre eso en los registros de la biblioteca."

    return respuesta_final


def responder_sobre_libros(pregunta, consulta):
    resultados = buscar_libros(consulta)

    return responder_con_contexto(
        pregunta,
        resultados,
        "No se encontraron coincidencias en el catálogo.",
    )


def responder_sobre_horarios(pregunta, consulta):
    resultados = buscar_horarios(consulta)

    return responder_con_contexto(
        pregunta,
        resultados,
        "No se encontraron coincidencias en los horarios.",
    )


def responder_sobre_eventos(pregunta, consulta):
    resultados = buscar_eventos(consulta)

    return responder_con_contexto(
        pregunta,
        resultados,
        "No se encontraron coincidencias en los eventos.",
    )


def responder_sobre_faq(pregunta, consulta):
    resultados = buscar_faq(consulta)

    return responder_con_contexto(
        pregunta,
        resultados,
        "No se encontraron coincidencias en las preguntas frecuentes.",
    )


def responder_sobre_politicas(pregunta, consulta):
    resultados = buscar_politicas(consulta)

    return responder_con_contexto(
        pregunta,
        resultados,
        "No se encontraron coincidencias en las políticas.",
    )