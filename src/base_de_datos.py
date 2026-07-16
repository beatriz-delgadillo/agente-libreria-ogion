"""
Este módulo sincroniza los archivos CSV hacia una base de datos SQLite interna que el agente usa para
buscar. Los CSV siguen siendo la fuente de verdad editable; la base
SQLite es solo un índice derivado que se reconstruye cada vez que se
llama a sincronizar().
"""

import sqlite3
from pathlib import Path

import pandas as pd

#Nuevas rutas para evitar bugs
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


def sincronizar():
    """Lee todos los CSV de data/ y los manda a una base SQLite,
    reemplazando el contenido anterior de cada tabla."""
    conn = sqlite3.connect(RUTA_DB)

    for nombre_tabla, nombre_csv in TABLAS.items():
        ruta_csv = CARPETA_DATOS / nombre_csv
        df = pd.read_csv(ruta_csv, encoding="utf-8-sig")
        df.to_sql(nombre_tabla, conn, if_exists="replace", index=False)

    conn.commit()
    conn.close()


def obtener_conexion():
    """Devuelve una conexión a la base SQLite ya sincronizada."""
    return sqlite3.connect(RUTA_DB)


if __name__ == "__main__":
    # Permite correr "python basededatos.py" directamente para sincronizar manualmente y ver qué tablas quedaron cargadas.
    sincronizar()
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print("Tablas creadas:", [fila[0] for fila in cursor.fetchall()])
    conn.close()