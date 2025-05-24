import pandas as pd
import sqlite3
import os

# Detectar si estamos dentro de un contenedor Docker (muy básico)
en_docker = os.path.exists("/.dockerenv")

# Ruta para guardar la base de datos
db_path = "/app/cartera_inversiones.db" if en_docker else "cartera_inversiones.db"
print(f"Creando base de datos en: {db_path}")

# Crear conexión a SQLite
conn = sqlite3.connect(db_path)

# Cargar archivos Excel
df_trans = pd.read_excel("transacciones.xlsx")
df_activos = pd.read_excel("activos_para_etiquetar.xlsx")

# Guardar en SQLite
df_trans.to_sql("transacciones", conn, if_exists="replace", index=False)
df_activos.to_sql("activos", conn, if_exists="replace", index=False)

conn.commit()
conn.close()

print("Base de datos 'cartera_inversiones.db' actualizada correctamente.")
