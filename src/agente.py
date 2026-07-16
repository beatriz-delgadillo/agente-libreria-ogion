import re

from lector_csv import leer_csv

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

def buscar_libros(consulta):
    catalogo = leer_csv("catalogo.csv")

    coincidencias = catalogo[
        catalogo["titulo"].str.contains(consulta, case=False, na=False)
        | catalogo["autor"].str.contains(consulta, case=False, na=False)
        | catalogo["genero"].str.contains(consulta, case=False, na=False)
    ]

    return coincidencias


def buscar_horarios(consulta):
    horarios = leer_csv("horarios.csv")

    coincidencias = horarios[
        horarios["dia"].str.contains(consulta, case=False, na=False)
    ]

    return coincidencias


def buscar_eventos(consulta):
    eventos = leer_csv("eventos.csv")

    coincidencias = eventos[
        eventos["nombre"].str.contains(consulta, case=False, na=False)
        | eventos["fecha"].str.contains(consulta, case=False, na=False)
        | eventos["descripcion"].str.contains(consulta, case=False, na=False)
        | eventos["publico"].str.contains(consulta, case=False, na=False)
    ]

    return coincidencias


def buscar_faq(consulta):
    faq = leer_csv("faq.csv")

    coincidencias = faq[
        faq["pregunta"].str.contains(consulta, case=False, na=False)
        | faq["respuesta"].str.contains(consulta, case=False, na=False)
    ]

    return coincidencias


def buscar_politicas(consulta):
    politicas = leer_csv("politicas.csv")

    coincidencias = politicas[
        politicas["categoria"].str.contains(consulta, case=False, na=False)
        | politicas["pregunta"].str.contains(consulta, case=False, na=False)
        | politicas["respuesta"].str.contains(consulta, case=False, na=False)
    ]

    return coincidencias

#Definicion de herramientas de respuesta con contexto


def formatear_contexto(df):
    """Convierte un DataFrame en bloques de texto tipo 'columna: valor',
    uno por fila, en vez de una tabla alineada con espacios (ambigua
    para modelos chicos)."""
    bloques = []
    for _, fila in df.iterrows():
        bloques.append("\n".join(f"{col}: {val}" for col, val in fila.items()))
    return "\n---\n".join(bloques)


def verificar_fidelidad(respuesta, contexto):
    """Revisa que los datos concretos (números, nombres propios) que
    aparecen en la respuesta del modelo también existan en el contexto
    recuperado. Si algo no aparece, es señal de posible alucinación.

    Tolera reformulaciones comunes de rangos numéricos, por ejemplo
    que el modelo escriba "3-7" cuando el contexto original dice
    "3 a 7", ya que es una paráfrasis válida y no un dato inventado.
    """
    tokens = re.findall(
        r'\b\d{1,4}(?:-\d+)*\b|\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,}\b', respuesta
    )

    faltantes = []
    for t in tokens:
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