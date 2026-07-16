"""
Script temporal para comparar modelos de Ollama en el flujo de Ogion.
NO reemplaza a main.py — es solo para decidir qué modelo usar.

Cómo usarlo:
1. Colócalo dentro de la carpeta src/ de tu proyecto (junto a agente.py).
2. Ejecútalo con: python comparar_modelos.py
3. Lee las respuestas de cada modelo para las mismas preguntas y decide
   cuál alucina menos.
"""

import ollama

from agente import (
    buscar_libros,
    buscar_horarios,
    buscar_eventos,
    buscar_politicas,
    buscar_faq,
    formatear_contexto,
    verificar_fidelidad,
)

# Ajusta estas dos líneas si quieres comparar otros modelos
MODELOS_A_COMPARAR = ["phi3", "llama3.2"]

SYSTEM_PROMPT = """
Eres Ogion, un asistente de biblioteca pública.

Reglas obligatorias:

1. Utiliza únicamente la información incluida en el contexto recuperado.
2. Nunca inventes información.
3. No deduzcas ni completes datos faltantes.
4. Si el contexto no contiene la respuesta, responde exactamente:
"No encontré información sobre eso en los registros de la biblioteca."
5. Responde de forma clara, breve y amable.
6. Tu prioridad absoluta es la precisión por encima de la creatividad.
"""

# Cada pregunta de prueba, con la función de búsqueda que le corresponde
# y la consulta que se usaría para buscar en el CSV.
PREGUNTAS_DE_PRUEBA = [
    ("¿Tienen el libro Rayuela?", buscar_libros, "Rayuela"),
    ("¿Cuál es el horario del domingo?", buscar_horarios, "domingo"),
    ("¿Qué eventos hay para niños?", buscar_eventos, "niños"),
    ("¿Cuántos libros puedo llevar a la vez?", buscar_politicas, "libros"),
    ("¿Tienen servicio de impresora?", buscar_faq, "impresora"),
    ("¿Qué información hay sobre un libro de cocina?", buscar_libros, "cocina"),
]


def preguntar_a_modelo(modelo, contexto, pregunta):
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
    respuesta = ollama.chat(
        model=modelo,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": mensaje},
        ],
        options={"temperature": 0},
    )
    return respuesta["message"]["content"]


def main():
    for pregunta, funcion_busqueda, consulta in PREGUNTAS_DE_PRUEBA:
        resultados = funcion_busqueda(consulta)

        print("=" * 70)
        print(f"PREGUNTA: {pregunta}")
        print("=" * 70)

        if resultados.empty:
            print("(sin coincidencias en el CSV para esta consulta)\n")
            continue

        contexto = formatear_contexto(resultados)

        for modelo in MODELOS_A_COMPARAR:
            respuesta = preguntar_a_modelo(modelo, contexto, pregunta)
            faltantes = verificar_fidelidad(respuesta, contexto)

            print(f"\n--- Modelo: {modelo} ---")
            print(respuesta)
            if faltantes:
                print(f"[!] Posibles datos no verificados en el contexto: {faltantes}")

        print()


if __name__ == "__main__":
    main()