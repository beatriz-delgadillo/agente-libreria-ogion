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


# Caracteres "tipográficos" que Word/Excel suelen sustituir automáticamente
# y que se ven idénticos a su versión normal a simple vista.
CARACTERES_A_ELIMINAR = {
    "\u2010": "",  # guion tipográfico
    "\u2011": "",  # guion de no separación
    "\u2012": "",  # guion de figura
    "\u2013": "",  # guion en (en dash)
    "\u2014": "",  # guion em (em dash)
    "-": "",       # guion normal
}

CARACTERES_TIPOGRAFICOS = {
    "\u00a0": " ",  # espacio de no separación
    "\u2018": "'", "\u2019": "'",  # comillas simples curvas
    "\u201c": '"', "\u201d": '"',  # comillas dobles curvas
}


def quitar_acentos(texto):
    """Quita tildes/acentos de un texto para que las búsquedas no
    dependan de que el usuario los escriba correctamente
    (ej. 'Miercoles' debe encontrar 'Miércoles'). De paso, elimina
    guiones (de cualquier variante tipográfica) y normaliza otros
    caracteres invisibles (espacios de no separación, comillas curvas)
    que Word/Excel insertan solos al editar texto, para que tampoco
    rompan la búsqueda (ej. 'wifi' debe encontrar 'Wi-Fi')."""
    if texto is None:
        return texto

    for original, reemplazo in CARACTERES_A_ELIMINAR.items():
        texto = texto.replace(original, reemplazo)
    for original, reemplazo in CARACTERES_TIPOGRAFICOS.items():
        texto = texto.replace(original, reemplazo)

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