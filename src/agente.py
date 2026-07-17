import re

import pandas as pd

from base_de_datos import obtener_conexion, quitar_acentos

import ollama

# Frase única de rechazo, usada en TODO el sistema
RESPUESTA_SIN_INFORMACION = "No tengo esa información, por favor consulta con un bibliotecario."


# definir mensaje ollama
def hablar_con_ollama(mensaje):
    respuesta = ollama.chat(
        model="phi3",
        messages=[
            {
                "role": "system",
                "content": f"""
Eres Ogion, un asistente de biblioteca pública.

Reglas obligatorias:


1. Utiliza únicamente la información incluida en el contexto recuperado.
2. Nunca inventes información.
3. No deduzcas ni completes datos faltantes.
4. Si el contexto no contiene la respuesta, responde ÚNICAMENTE con esta frase, sin agregar nada antes ni después:
"{RESPUESTA_SIN_INFORMACION}"
5. Responde de forma clara, breve y amable.
6. Tu prioridad absoluta es la precisión por encima de la creatividad.
7. Nunca comentes sobre errores ortográficos, de redacción o de gramática en la pregunta del usuario. Interpreta su intención lo mejor posible y responde directamente con la información del contexto.
8. Nunca expliques por qué no puedes responder, ni razones en voz alta sobre el alcance de la pregunta. Si no puedes responder, usa exactamente la frase de la regla 4 y nada más.
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

#Definicion de herramientas de busqueda (ahora contra SQLite, no CSV directo)

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
        p for p in limpio.split()
        if p and p not in PALABRAS_VACIAS and (p.isdigit() or len(p) > 2)
    ]
    return palabras or [consulta.strip()]


def variantes_palabra(palabra):
    """Genera variantes simples de singular/plural de una palabra, para
    que buscar 'novelas' también encuentre filas que dicen 'Novela'
    (y viceversa), cubriendo los dos patrones más comunes del español:
    agregar/quitar 's' (libro/libros) y agregar/quitar 'es'
    (taller/talleres). No cubre plurales irregulares, pero resuelve
    la gran mayoría de los casos reales."""
    variantes = {palabra}

    if palabra.endswith("es") and len(palabra) > 5:
        variantes.add(palabra[:-2])
    if palabra.endswith("s") and len(palabra) > 4:
        variantes.add(palabra[:-1])
    if not palabra.endswith("s"):
        variantes.add(palabra + "s")
        variantes.add(palabra + "es")

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


def verificar_fidelidad(respuesta, contexto):
    """Revisa que los datos concretos (números y nombres propios/títulos)
    que aparecen en la respuesta del modelo también existan en el
    contexto recuperado. Si algo no aparece, es señal de posible
    alucinación.

    A propósito solo marca:
    - Números (ISBN, precios, cantidades, años).
    - Frases de DOS O MÁS palabras seguidas con mayúscula inicial
      (ej. "Harry Potter", "Julio Cortázar"), que es como se ven los
      nombres propios y títulos reales o inventados.

    Una sola palabra capitalizada suelta (ej. "Tenemos", "Novela") ya
    NO se marca, porque casi siempre es solo el inicio de una oración
    y no un dato en sí — marcarlas generaba demasiados falsos positivos
    que rechazaban respuestas correctas.

    Tolera reformulaciones comunes de rangos numéricos, por ejemplo
    que el modelo escriba "3-7" cuando el contexto original dice
    "3 a 7", ya que es una paráfrasis válida y no un dato inventado.
    """
    numeros = re.findall(r'\b\d{1,4}(?:-\d+)*\b', respuesta)
    frases_propias = re.findall(
        r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]*(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]*)+\b',
        respuesta,
    )
    candidatos = numeros + frases_propias

    articulos = {"el", "la", "los", "las", "un", "una", "unos", "unas"}

    faltantes = []
    for t in candidatos:
        if t in contexto:
            continue

        # El modelo suele anteponer un artículo al nombre real
        primera_palabra, _, resto = t.partition(" ")
        if primera_palabra.lower() in articulos and resto and resto in contexto:
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
4. Si el contexto no contiene la respuesta exacta, responde ÚNICAMENTE, sin nada antes ni después:
"{RESPUESTA_SIN_INFORMACION}"
5. Puedes resumir, pero no añadir ningún dato nuevo.
6. Sé breve y directo. No expliques por qué no puedes responder.

Respuesta:
"""

    respuesta_final = hablar_con_ollama(mensaje)

    faltantes = verificar_fidelidad(respuesta_final, contexto)
    if faltantes:
        return RESPUESTA_SIN_INFORMACION

    return respuesta_final


def responder_sobre_libros(pregunta, consulta):
    resultados = buscar_libros(consulta)

    return responder_con_contexto(pregunta, resultados, RESPUESTA_SIN_INFORMACION)


def responder_sobre_horarios(pregunta, consulta):
    resultados = buscar_horarios(consulta)

    return responder_con_contexto(pregunta, resultados, RESPUESTA_SIN_INFORMACION)


def responder_sobre_eventos(pregunta, consulta):
    resultados = buscar_eventos(consulta)

    return responder_con_contexto(pregunta, resultados, RESPUESTA_SIN_INFORMACION)


def responder_sobre_faq(pregunta, consulta):
    resultados = buscar_faq(consulta)

    return responder_con_contexto(pregunta, resultados, RESPUESTA_SIN_INFORMACION)


def responder_sobre_politicas(pregunta, consulta):
    resultados = buscar_politicas(consulta)

    return responder_con_contexto(pregunta, resultados, RESPUESTA_SIN_INFORMACION)


#Definicion del clasificador de intencion (para la caja de texto libre)

# Cada categoría tiene palabras clave con un "peso": las palabras muy
# específicas de esa categoría valen 2 puntos, las genéricas (que
# también podrían aparecer en otras categorías) valen 1 punto. Esto
# ayuda a resolver casos ambiguos, por ejemplo "¿Cuántos libros puedo
# pedir prestados?" contiene "libros" (genérico, categoría libros) pero
# también "prestados" (específico, categoría políticas) — y políticas
# debe ganar ahí, porque es una pregunta sobre reglas de préstamo, no
# sobre buscar un libro en el catálogo.
CATEGORIAS = {
    "libros": {
        "autor": 2, "autora": 2, "isbn": 2, "catalogo": 2, "novela": 2,
        "novelas": 2, "genero": 2, "género": 2, "titulo": 2, "título": 2,
        "libro": 1, "libros": 1,
    },
    "horarios": {
        "horario": 2, "horarios": 2, "abren": 2, "cierran": 2, "apertura": 2,
        "cierre": 2, "abierto": 2, "cerrado": 2, "lunes": 2, "martes": 2,
        "miercoles": 2, "jueves": 2, "viernes": 2, "sabado": 2, "domingo": 2,
        "hora": 1,
    },
    "eventos": {
        "evento": 2, "eventos": 2, "taller": 2, "talleres": 2,
        "actividad": 2, "actividades": 2, "club": 2, "cuentacuentos": 2,
        "manualidades": 2, "presentacion": 2,
    },
    "faq": {
        "impresora": 2, "imprimir": 2, "fotocopia": 2, "fotocopiadora": 2,
        "wifi": 2, "internet": 2, "computadora": 2, "computadoras": 2,
        "bano": 2, "servicio": 1, "servicios": 1,
    },
    "politicas": {
        "politica": 2, "politicas": 2, "prestamo": 2, "prestamos": 2,
        "credencial": 2, "multa": 2, "multas": 2, "renovar": 2,
        "renovacion": 2, "devolver": 2, "devolucion": 2, "requisito": 2,
        "requisitos": 2, "limite": 2, "prestar": 2, "prestado": 2,
        "prestados": 2, "prestada": 2, "prestadas": 2,
    },
}

BUSCADORES = {
    "libros": (buscar_libros, RESPUESTA_SIN_INFORMACION),
    "horarios": (buscar_horarios, RESPUESTA_SIN_INFORMACION),
    "eventos": (buscar_eventos, RESPUESTA_SIN_INFORMACION),
    "faq": (buscar_faq, RESPUESTA_SIN_INFORMACION),
    "politicas": (buscar_politicas, RESPUESTA_SIN_INFORMACION),
}


def clasificar_intencion(pregunta):
    """Devuelve una lista de categorías candidatas, ordenadas de la más
    probable a la menos probable, según las palabras clave encontradas
    en la pregunta. Si ninguna palabra clave hace match, devuelve una
    lista vacía."""
    limpio = quitar_acentos(re.sub(r"[¿?¡!.,;:]", " ", pregunta.lower()))
    palabras = limpio.split()

    puntajes = {categoria: 0 for categoria in CATEGORIAS}
    for palabra in palabras:
        for categoria, palabras_clave in CATEGORIAS.items():
            if palabra in palabras_clave:
                puntajes[categoria] += palabras_clave[palabra]

    candidatas = sorted(
        (categoria for categoria, puntos in puntajes.items() if puntos > 0),
        key=lambda categoria: puntajes[categoria],
        reverse=True,
    )
    return candidatas


def _fue_respuesta_fallida(respuesta):
    # Se usa "in" (no "startswith") a propósito: si el modelo llegara a
    # agregar texto antes de la frase de rechazo pese a la instrucción,
    # esto la sigue detectando y prueba la siguiente categoría en vez
    # de quedarse con una respuesta con explicaciones de más.
    return RESPUESTA_SIN_INFORMACION in respuesta


def responder(pregunta):
    """Punto de entrada único para la caja de texto libre: prueba las
    categorías en orden de probabilidad (según el clasificador) y, si
    una categoría encuentra filas pero la respuesta generada termina
    siendo un "no sé" (porque esas filas en realidad no respondían la
    pregunta), prueba la siguiente categoría en vez de rendirse ahí.
    Si el clasificador no dio ninguna pista, se prueban todas."""
    candidatas = clasificar_intencion(pregunta)
    orden = candidatas + [c for c in BUSCADORES if c not in candidatas]

    for categoria in orden:
        buscar_funcion, mensaje_vacio = BUSCADORES[categoria]
        resultados = buscar_funcion(pregunta)
        if resultados.empty:
            continue

        respuesta = responder_con_contexto(pregunta, resultados, mensaje_vacio)
        if not _fue_respuesta_fallida(respuesta):
            return respuesta

    return RESPUESTA_SIN_INFORMACION