# archivo: app.py
import streamlit as st

st.set_page_config(page_title="Dashboard de Inversiones", layout="wide")

st.title("📊 Dashboard de Inversiones")

st.markdown("""
Bienvenido al sistema de análisis y gestión de tu cartera de inversiones.

Utiliza el menú lateral izquierdo para navegar entre las distintas funcionalidades:
- Visualizar KPIs, rentabilidad y transacciones
- Registrar nuevos movimientos
- (Opcional) Analizar escenarios futuros
""")
