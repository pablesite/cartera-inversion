import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from helper import (
    xirr,
    calcular_tir_desde_df,
    calcular_rentabilidad_por_activo,
    calcular_tir_acumulado_en_tiempo,
    calcular_rentabilidad_anual,
    calcular_tir_anual
)

# --- Cargar datos ---
conn = sqlite3.connect("cartera_inversiones.db")
trans = pd.read_sql("SELECT * FROM transacciones", conn)
activos = pd.read_sql("SELECT * FROM activos", conn)
conn.close()

# --- Unir y preparar ---
df = trans.merge(activos, on="activo", how="left")
df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
df["importe_euros"] = pd.to_numeric(df["importe_euros"], errors="coerce")

# --- Filtros ---
min_date, max_date = df["fecha"].min(), df["fecha"].max()
start_date, end_date = st.sidebar.date_input("Rango de fechas", [min_date, max_date], min_value=min_date, max_value=max_date)
activo_sel = st.sidebar.multiselect("Activo", options=df["activo"].unique(), default=df["activo"].unique())
tipo_sel = st.sidebar.multiselect("Tipo de operación", options=df["tipo_operacion"].unique(), default=df["tipo_operacion"].unique())

# --- Aplicar filtros ---
df = df[(df["fecha"] >= pd.to_datetime(start_date)) & (df["fecha"] <= pd.to_datetime(end_date))]
df_filtrado = df[df["activo"].isin(activo_sel) & df["tipo_operacion"].isin(tipo_sel)]

# --- KPIs generales ---
aporte_compras = df_filtrado.query("tipo_operacion == 'aporte' and subtipo_operacion == 'compra'")["importe_euros"].sum()
retiradas = df_filtrado.query("tipo_operacion == 'retirada' and subtipo_operacion == 'retirada'")["importe_euros"].sum()
aporte_reinv = df_filtrado.query("tipo_operacion == 'aporte' and subtipo_operacion.str.startswith('reinv')", engine="python")["importe_euros"].sum()
ajuste_perdida = df_filtrado.query("tipo_operacion == 'retirada' and subtipo_operacion == 'ajuste_por_perdida'")["importe_euros"].sum()

aporte_bruto_compras = aporte_compras + retiradas
aporte_bruto_reinv = aporte_reinv + ajuste_perdida
aporte_neto = aporte_bruto_compras + aporte_bruto_reinv

beneficios = df_filtrado.query("tipo_operacion == 'beneficio'")["importe_euros"].sum()
perdidas = df_filtrado.query("tipo_operacion == 'perdida'")["importe_euros"].sum()
beneficio_bruto = beneficios + perdidas

beneficio_flotante = df_filtrado.query("tipo_operacion == 'otro' and subtipo_operacion in ['revalorizacion', 'devaluacion']")["importe_euros"].sum()
beneficio_neto = beneficio_bruto + beneficio_flotante
valor_actual = aporte_neto + beneficio_flotante

rent_total_con = (beneficio_neto / aporte_neto * 100) if aporte_neto else 0
rent_total_sin = (beneficio_neto / aporte_bruto_compras * 100) if aporte_bruto_compras else 0

# --- Mostrar KPIs ---
st.subheader("Valor actual de la cartera")
st.metric("Valor actual estimado", f"{valor_actual:,.2f} €")

st.subheader("Resumen de KPIs filtrados")
col1, col2, col3 = st.columns(3)
col1.metric("Aporte Bruto", f"{aporte_bruto_compras:,.2f} €")
col2.metric("Aporte Reinv - Pér", f"{aporte_bruto_reinv:,.2f} €")
col3.metric("Aporte Neto", f"{aporte_neto:,.2f} €")

col4, col5, col6 = st.columns(3)
col4.metric("Beneficio Consolidado", f"{beneficio_bruto:,.2f} €")
col5.metric("Beneficio Flotante", f"{beneficio_flotante:,.2f} €")
col6.metric("Beneficio Neto", f"{beneficio_neto:,.2f} €")

tir_total = calcular_tir_desde_df(df_filtrado, valor_actual)
col7, col8, _ = st.columns(3)
col7.metric("Rentabilidad total (%)", f"{rent_total_sin:.2f} %")
col8.metric("TIR Cartera", f"{tir_total * 100:.2f} %" if tir_total else "No disponible")

# --- Rentabilidad por activo ---
st.subheader("Rentabilidad porcentual por activo")
df_rentabilidad = calcular_rentabilidad_por_activo(df_filtrado)
if not df_rentabilidad.empty:
    st.dataframe(
        df_rentabilidad.sort_values("TIR %", ascending=False),
        column_config={
            "aportado": st.column_config.NumberColumn(format="%.2f €"),
            "beneficio_consolidado": st.column_config.NumberColumn(format="%.2f €"),
            "valor_flotante": st.column_config.NumberColumn(format="%.2f €"),
            "beneficio_neto": st.column_config.NumberColumn(format="%.2f €"),
            "valor_actual": st.column_config.NumberColumn(format="%.2f €"),
            "% rentabilidad_total": st.column_config.NumberColumn(format="%.2f %%"),
            "TIR %": st.column_config.NumberColumn(format="%.2f %%")
        }
    )
else:
    st.info("No hay resultados para mostrar o falta la columna TIR %.")



# --- Rentabilidad mensual: flotante, neta y porcentaje sobre aportes ---
df_mes = df_filtrado.copy()
df_mes["mes"] = df_mes["fecha"].dt.to_period("M").dt.to_timestamp()

flot_mes = df_mes[df_mes["subtipo_operacion"].isin(["revalorizacion", "devaluacion"])].groupby("mes")["importe_euros"].sum().reset_index(name="flotante")
net_mes = df_mes[df_mes["tipo_operacion"].isin(["beneficio", "perdida", "pérdida"])].groupby("mes")["importe_euros"].sum().reset_index(name="neta")
aport_mes = df_mes[df_mes["tipo_operacion"].isin(["aporte", "comision"])].groupby("mes")["importe_euros"].sum().reset_index(name="aportado")

mensual = pd.merge(flot_mes, net_mes, on="mes", how="outer")
mensual = pd.merge(mensual, aport_mes, on="mes", how="outer")
mensual = mensual.fillna(0).sort_values("mes")

mensual["% flotante"] = mensual.apply(lambda r: r["flotante"] / r["aportado"] * 100 if r["aportado"] > 0 else 0, axis=1)
mensual["% neta"] = mensual.apply(lambda r: r["neta"] / r["aportado"] * 100 if r["aportado"] > 0 else 0, axis=1)

# --- Gráfico de barras: beneficio en euros ---
fig_beneficio_eur = go.Figure()
fig_beneficio_eur.add_trace(go.Bar(x=mensual["mes"], y=mensual["flotante"], name="Flotante", marker_color="gold"))
fig_beneficio_eur.add_trace(go.Bar(x=mensual["mes"], y=mensual["neta"], name="Consolidado", marker_color="steelblue"))
fig_beneficio_eur.update_layout(
    title="Beneficio mensual por tipo (€)",
    xaxis_title="Mes",
    yaxis_title="Importe €",
    barmode="group",
    hovermode="x unified"
)
st.plotly_chart(fig_beneficio_eur, use_container_width=True)



# --- Evolución del TIR acumulado en el tiempo ---
df_tir_tiempo = calcular_tir_acumulado_en_tiempo(df_filtrado)

if not df_tir_tiempo.empty and "fecha" in df_tir_tiempo.columns and "TIR %" in df_tir_tiempo.columns:
    tir = df_tir_tiempo["TIR %"]
    fechas = df_tir_tiempo["fecha"]
    tir_pos = tir.where(tir > 0, 0)
    tir_neg = tir.where(tir < 0, 0)

    fig_tir = go.Figure()
    fig_tir.add_trace(go.Scatter(x=fechas, y=tir_pos, fill='tozeroy', mode='none', fillcolor='rgba(0, 200, 0, 0.3)', name='Zona positiva'))
    fig_tir.add_trace(go.Scatter(x=fechas, y=tir_neg, fill='tozeroy', mode='none', fillcolor='rgba(200, 0, 0, 0.3)', name='Zona negativa'))
    fig_tir.add_trace(go.Scatter(x=fechas, y=tir, mode='lines+markers', line=dict(color='lightblue', width=2), name='TIR acumulada'))
    fig_tir.add_shape(type="line", x0=fechas.min(), y0=0, x1=fechas.max(), y1=0, line=dict(color="white", width=1, dash="dash"))
    fig_tir.update_layout(title='Evolución del TIR acumulado', xaxis_title='Fecha', yaxis_title='TIR %', hovermode="x unified")
    st.plotly_chart(fig_tir)
else:
    st.info("No hay datos para mostrar en el gráfico de TIR acumulado.")

# --- Rentabilidad acumulada en € y % ---
df_flot = df_filtrado[df_filtrado["subtipo_operacion"].isin(["revalorizacion", "devaluacion"])]
df_net = df_filtrado[df_filtrado["tipo_operacion"].isin(["beneficio", "perdida", "pérdida"])]
df_aport = df_filtrado[df_filtrado["tipo_operacion"].isin(["aporte", "comision"])]

aportado = df_aport.groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="aportado")
neta = df_net.groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="neta")
flotante = df_flot.groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="flotante")

area = aportado.merge(neta, on="fecha", how="outer").merge(flotante, on="fecha", how="outer").sort_values("fecha").ffill().fillna(0)
area["% neta"] = area.apply(lambda r: r["neta"] / r["aportado"] * 100 if r["aportado"] > 0 else 0, axis=1)
area["% flotante"] = area.apply(lambda r: r["flotante"] / r["aportado"] * 100 if r["aportado"] > 0 else 0, axis=1)

fig_area = make_subplots(rows=1, cols=2, subplot_titles=["Beneficio acumulado (€)", "Rentabilidad acumulada (%)"], shared_xaxes=False)
fig_area.add_trace(go.Scatter(x=area["fecha"], y=area["flotante"], fill="tozeroy", name="Flotante €", line=dict(color="gold"), opacity=0.4), row=1, col=1)
fig_area.add_trace(go.Scatter(x=area["fecha"], y=area["neta"], fill="tonexty", name="Consolidado €", line=dict(color="steelblue")), row=1, col=1)
fig_area.add_trace(go.Scatter(x=area["fecha"], y=area["% flotante"], fill="tozeroy", name="Flotante %", line=dict(color="gold"), opacity=0.4), row=1, col=2)
fig_area.add_trace(go.Scatter(x=area["fecha"], y=area["% neta"], fill="tonexty", name="Consolidado %", line=dict(color="steelblue")), row=1, col=2)
fig_area.update_xaxes(title_text="Fecha", row=1, col=1)
fig_area.update_yaxes(title_text="€ acumulado", row=1, col=1)
fig_area.update_xaxes(title_text="Fecha", row=1, col=2)
fig_area.update_yaxes(title_text="% sobre aportado", row=1, col=2)
fig_area.update_layout(title="Beneficio en euros vs rentabilidad en %", hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5))
st.plotly_chart(fig_area, use_container_width=True)

# --- Rentabilidad anual ---
df_rent = calcular_rentabilidad_anual(df_filtrado)
df_tir = calcular_tir_anual(df_filtrado, xirr)
df_final = df_rent.merge(df_tir, on="año", how="left")

st.subheader("Rentabilidad anual (% y €)")
st.dataframe(df_final)

fig_year = go.Figure()
fig_year.add_trace(go.Bar(x=df_final["año"], y=df_final["% rentabilidad total"], name="Rentabilidad Total (%)"))
fig_year.add_trace(go.Scatter(x=df_final["año"], y=df_final["TIR %"], name="TIR (%)", mode="lines+markers", yaxis="y2"))

y_min = min(df_final["% rentabilidad total"].min(), df_final["TIR %"].min())
y_max = max(df_final["% rentabilidad total"].max(), df_final["TIR %"].max())
y_min = int(y_min) - 5
y_max = int(y_max) + 5

fig_year.update_layout(
    title="Rentabilidad anual: % total vs TIR",
    xaxis_title="Año",
    yaxis=dict(title="% Rentabilidad", range=[y_min, y_max]),
    yaxis2=dict(title="TIR %", overlaying="y", side="right", range=[y_min, y_max]),
    legend=dict(orientation="h", y=1.1),
    hovermode="x unified"
)

st.plotly_chart(fig_year)

# --- Transacciones ---
st.subheader("Transacciones filtradas")
st.dataframe(df_filtrado.sort_values("fecha", ascending=False))





