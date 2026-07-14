from lector_csv import leer_csv
import ollama

def hablar_con_ollama(mensaje):
    respuesta = ollama.chat(
        model="phi3",
        messages=[
            {
                "role": "user",
                "content": mensaje
            }
        ]
    )

    return respuesta["message"]["content"]


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