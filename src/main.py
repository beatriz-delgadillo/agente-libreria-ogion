from agente import (
    responder_sobre_eventos,
    responder_sobre_faq,
    responder_sobre_horarios,
    responder_sobre_libros,
    responder_sobre_politicas,
)


def mostrar_menu():
    print("\n📚 Bienvenido a Ogion, asistente de la biblioteca\n")
    print("1. Buscar libros")
    print("2. Consultar horarios")
    print("3. Consultar eventos")
    print("4. Consultar preguntas frecuentes")
    print("5. Consultar políticas")
    print("0. Salir")


while True:
    mostrar_menu()
    opcion = input("\nSelecciona una opción: ").strip()

    if opcion == "1":
        consulta = input("Escribe el título, autor o género: ").strip()
        pregunta = f"¿Qué información hay sobre {consulta}?"
        respuesta = responder_sobre_libros(pregunta, consulta)

    elif opcion == "2":
        consulta = input("Escribe un día de la semana: ").strip()
        pregunta = f"¿Cuál es el horario del {consulta}?"
        respuesta = responder_sobre_horarios(pregunta, consulta)

    elif opcion == "3":
        consulta = input(
            "Escribe el nombre, fecha, descripción o público del evento: "
        ).strip()
        pregunta = f"¿Qué información hay sobre eventos relacionados con {consulta}?"
        respuesta = responder_sobre_eventos(pregunta, consulta)

    elif opcion == "4":
        consulta = input("Escribe una palabra clave: ").strip()
        pregunta = f"¿Qué información frecuente hay sobre {consulta}?"
        respuesta = responder_sobre_faq(pregunta, consulta)

    elif opcion == "5":
        consulta = input("Escribe una palabra clave: ").strip()
        pregunta = f"¿Qué política existe sobre {consulta}?"
        respuesta = responder_sobre_politicas(pregunta, consulta)

    elif opcion == "0":
        print("\nOgion: Hasta luego.")
        break

    else:
        print("\nOgion: Opción no válida.")
        continue

    print(f"\nOgion: {respuesta}")