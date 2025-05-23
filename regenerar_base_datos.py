import pandas as pd
import sqlite3

# Cargar archivos
df_trans = pd.read_excel("transacciones.xlsx")
df_activos = pd.read_excel("activos_para_etiquetar.xlsx")

# Crear base de datos
conn = sqlite3.connect("cartera_inversiones.db")
df_trans.to_sql("transacciones", conn, if_exists="replace", index=False)
df_activos.to_sql("activos", conn, if_exists="replace", index=False)
conn.close()

print("Base de datos 'cartera_inversiones.db' actualizada correctamente.")