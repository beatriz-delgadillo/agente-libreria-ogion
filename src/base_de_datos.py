"""
Este módulo sincroniza los archivos CSV (que los bibliotecarios editan
en Excel) hacia una base de datos SQLite interna que el agente usa para
buscar. Los CSV siguen siendo la fuente de verdad editable; la base
SQLite es solo un índice derivado que se reconstruye cada vez que se
llama a sincronizar().
"""

import sqlite3
import unicodedata
from pathlib import Path

import pandas as pd

# Rutas calculadas a partir de la ubicación de este archivo, no del
# directorio desde donde se ejecuta el programa (evita el bug de rutas
# relativas frágiles que dependían del cwd).
CARPETA_PROYECTO = Path(__file__).resolve().parent.parent
CARPETA_DATOS = CARPETA_PROYECTO / "data"
RUTA_DB = CARPETA_PROYECTO / "ogion_index.db"

TABLAS = {
    "catalogo": "catalogo.csv",
    "horarios": "horarios.csv",
    "eventos": "eventos.csv",
    "faq": "faq.csv",
    "politicas": "politicas.csv",
}


def quitar_acentos(texto):
    """Quita tildes/acentos de un texto para que las búsquedas no
    dependan de que el usuario los escriba correctamente
    (ej. 'Miercoles' debe encontrar 'Miércoles')."""
    if texto is None:
        return texto
    forma_descompuesta = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in forma_descompuesta if not unicodedata.combining(c))


def sincronizar():
    """Lee todos los CSV de data/ y los vuelca a la base SQLite,
    reemplazando el contenido anterior de cada tabla."""
    conn = sqlite3.connect(RUTA_DB)

    for nombre_tabla, nombre_csv in TABLAS.items():
        ruta_csv = CARPETA_DATOS / nombre_csv
        df = pd.read_csv(ruta_csv, encoding="utf-8-sig")
        df.to_sql(nombre_tabla, conn, if_exists="replace", index=False)

    conn.commit()
    conn.close()


def obtener_conexion():
    """Devuelve una conexión a la base SQLite ya sincronizada, con la
    función quitar_acentos disponible para usarse dentro de consultas SQL."""
    conn = sqlite3.connect(RUTA_DB)
    conn.create_function("quitar_acentos", 1, quitar_acentos)
    return conn


if __name__ == "__main__":
    # Permite correr "python basededatos.py" directamente para
    # sincronizar manualmente y ver qué tablas quedaron cargadas.
    sincronizar()
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print("Tablas creadas:", [fila[0] for fila in cursor.fetchall()])
    conn.close()