import sqlite3
import pandas as pd

# Ruta de la base de datos
db_path = "cartera_inversiones.db"

# Conexión y consulta
conn = sqlite3.connect(db_path)
df_transacciones = pd.read_sql("SELECT * FROM transacciones", conn)
conn.close()

# Exportar a Excel
excel_path = "transacciones.xlsx"
df_transacciones.to_excel(excel_path, index=False)

print(f"✔️ Archivo actualizado: {excel_path}")
