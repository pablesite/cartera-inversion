import pandas as pd

# Cargar el Excel
archivo = "transacciones.xlsx"
df = pd.read_excel(archivo)

# Asegurar que las columnas estén en formato string (si vienen como datetime o float)
df["fecha"] = df["fecha"].astype(str)
df["hora"] = df["hora"].astype(str)

# Unir y convertir a datetime
df["fecha_hora"] = pd.to_datetime(df["fecha"] + " " + df["hora"], errors="coerce")

# Guardar nuevo Excel con la columna combinada
df.to_excel("transacciones_con_fecha_hora.xlsx", index=False)
