
#Interfaz web de Ogion usando Gradio.

import gradio as gr

from base_de_datos import sincronizar
from agente import responder

# Sincroniza los CSV hacia SQLite al arrancar el servidor
sincronizar()


def responder_chat(mensaje, historial):
    """Gradio le pasa a esta función el mensaje nuevo y el historial de
    la conversación. Ogion no usa el historial (cada pregunta se
    responde de forma independiente, como ya lo hacía en la terminal),
    así que lo ignoramos y solo usamos el mensaje actual."""
    return responder(mensaje)


demo = gr.ChatInterface(
    fn=responder_chat,
    title="📚 Ogion - Asistente de Biblioteca",
    description=(
        '<div style="text-align: center;"><strong>'
        "Pregúntame sobre libros, horarios, eventos, servicios o "
        "políticas de la biblioteca. Intenta evitar errores "
        "ortográficos, el modelo es sensible a ellos. Y tenme "
        "paciencia, soy algo lento."
        "</strong></div>"
    ),
    examples=[
        "¿Tienen libros de Isabel Allende?",
        "¿A qué hora abren los sábados?",
        "¿Qué eventos hay para niños?",
        "¿Cuáles son las políticas de préstamo?",
    ],
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)