import pandas as pd
import sqlite3

db_path = "/app/cartera_inversiones.db"
print(f"Creando base de datos en: {db_path}")

conn = sqlite3.connect(db_path)

# Cargar archivos
df_trans = pd.read_excel("transacciones.xlsx")
df_activos = pd.read_excel("activos_para_etiquetar.xlsx")

df_trans.to_sql("transacciones", conn, if_exists="replace", index=False)
df_activos.to_sql("activos", conn, if_exists="replace", index=False)

conn.commit()
conn.close()

print("Base de datos 'cartera_inversiones.db' actualizada correctamente.")
