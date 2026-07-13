import pandas as pd

def leer_csv(nombre_archivo):
    datos = pd.read_csv(f"data/{nombre_archivo}")
    return datos