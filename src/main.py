from base_de_datos import sincronizar

from agente import (
    responder_sobre_eventos,
    responder_sobre_faq,
    responder_sobre_horarios,
    responder_sobre_libros,
    responder_sobre_politicas,
)

# Sincroniza los CSV a la base SQLite interna cada vez que arranca el programa
sincronizar()


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
        consulta = input("Escribe el título, autor o género (puede ser una pregunta completa): ").strip()
        respuesta = responder_sobre_libros(consulta, consulta)

    elif opcion == "2":
        consulta = input("Escribe un día de la semana (puede ser una pregunta completa): ").strip()
        respuesta = responder_sobre_horarios(consulta, consulta)

    elif opcion == "3":
        consulta = input(
            "Escribe el nombre, fecha, descripción o público del evento (puede ser una pregunta completa): "
        ).strip()
        respuesta = responder_sobre_eventos(consulta, consulta)

    elif opcion == "4":
        consulta = input("Escribe tu pregunta o una palabra clave: ").strip()
        respuesta = responder_sobre_faq(consulta, consulta)

    elif opcion == "5":
        consulta = input("Escribe tu pregunta o una palabra clave: ").strip()
        respuesta = responder_sobre_politicas(consulta, consulta)

    elif opcion == "0":
        print("\nOgion: Hasta luego.")
        break

    else:
        print("\nOgion: Opción no válida.")
        continue

    print(f"\nOgion: {respuesta}")