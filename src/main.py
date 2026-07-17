from base_de_datos import sincronizar
from agente import responder

# Sincroniza los CSV (editables por los bibliotecarios en Excel) hacia
# la base SQLite interna cada vez que arranca el programa.
sincronizar()

print("📚 Bienvenido a Ogion, asistente de la biblioteca")
print("Escribe tu pregunta libremente (libros, horarios, eventos, servicios o políticas).")
print("Escribe 'salir' para terminar.\n")

while True:
    pregunta = input("Tú: ").strip()

    if not pregunta:
        continue

    if pregunta.lower() in ("salir", "exit", "salir.", "0"):
        print("\nOgion: Hasta luego.")
        break

    respuesta = responder(pregunta)
    print(f"\nOgion: {respuesta}\n")