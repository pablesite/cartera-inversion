import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime
import requests

st.subheader("Registrar nuevo movimiento")

# Leer activos desde la base de datos
conn = sqlite3.connect("cartera_inversiones.db")
activos_df = pd.read_sql("SELECT DISTINCT activo FROM activos", conn)
conn.close()
opciones_activos = sorted(activos_df["activo"].dropna().unique())

# Diccionario de subtipos
subtipos_dict = {
    "aporte": ["compra", "reinv_benef", "reinv_recom"],
    "retirada": ["retirada", "ajuste_por_perdida"],
    "comision": ["comision_compra", "comision_venta"],
    "beneficio": ["cashback", "venta", "dividendo", "interes"],
    "perdida": ["venta"],
    "otro": ["revalorizacion", "devaluacion", "ajuste"]
}

# Utilizar estado de sesión para almacenar selección y forzar rerun
if "tipo_operacion" not in st.session_state:
    st.session_state.tipo_operacion = "aporte"

tipo_operacion = st.selectbox("Tipo de operación", list(subtipos_dict.keys()),
                                index=list(subtipos_dict.keys()).index(st.session_state.tipo_operacion),
                                on_change=lambda: st.session_state.update(tipo_operacion=st.session_state.tipo_operacion))

# Subtipos actualizados dinámicamente
subtipo_opciones = subtipos_dict.get(tipo_operacion, [])

with st.form("form_movimiento"):
    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("Fecha", value=datetime.today())
        hora = st.time_input("Hora", value=datetime.now().time())
        activo = st.selectbox("Activo", opciones_activos)
        importe = st.number_input("Importe en euros", format="%.2f")
    with col2:
        subtipo_operacion = st.selectbox("Subtipo de operación", subtipo_opciones)
        moneda = st.selectbox("Moneda", ["EUR", "USD"])
        usuario = st.text_input("Usuario", value="Pablo")

    submitted = st.form_submit_button("Guardar movimiento")

    tipo_cambio = 1.0
    if moneda == "USD":
        try:
            response = requests.get("https://v6.exchangerate-api.com/v6/013d1a2c2928ad7aaa14e76c/latest/USD")
            data = response.json()
            if data.get("result") == "success":
                tipo_cambio = data["conversion_rates"].get("EUR", 1.0)
                tipo_cambio = 1/tipo_cambio
                st.info(f"Tipo de cambio USD → EUR: {tipo_cambio:.4f}")
            else:
                st.warning("No se pudo obtener tipo de cambio válido. Se usará 1.0 por defecto.")
        except Exception as e:
            st.error(f"Error al obtener el tipo de cambio. Se usará 1.0. ({e})")


    if submitted:
        try:
            fecha_hora = datetime.combine(fecha, hora)
            conn = sqlite3.connect("cartera_inversiones.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transacciones (
                    fecha_hora, activo, importe_original, moneda,
                    tipo_cambio, importe_euros, etiqueta, tipo_operacion,
                    subtipo_operacion, porcentaje_participacion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fecha_hora.strftime("%Y-%m-%d %H:%M:%S"),
                activo, importe, moneda, tipo_cambio,
                importe / tipo_cambio, usuario,
                tipo_operacion, subtipo_operacion, 1.0
            ))
            conn.commit()
            conn.close()
            st.success("Movimiento registrado con éxito. Redirigiendo al dashboard...")
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar el movimiento: {e}")
