import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Conexión a la base de datos
conn = sqlite3.connect("cartera_inversiones.db")

# Cargar datos
trans = pd.read_sql("SELECT * FROM transacciones", conn)
activos = pd.read_sql("SELECT * FROM activos", conn)
conn.close()

# Unir ambas tablas por activo
df = trans.merge(activos, on="activo", how="left")
df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

# ===================== Filtro temporal =====================
min_date = df["fecha"].min()
max_date = df["fecha"].max()
start_date, end_date = st.sidebar.date_input("Rango de fechas", [min_date, max_date], min_value=min_date, max_value=max_date)
df = df[(df["fecha"] >= pd.to_datetime(start_date)) & (df["fecha"] <= pd.to_datetime(end_date))]

# ===================== Filtros de selección =====================
st.sidebar.header("Filtros")
activo_sel = st.sidebar.multiselect("Activo", options=df["activo"].unique(), default=df["activo"].unique())
tipo_sel = st.sidebar.multiselect("Tipo de operación", options=df["tipo_operacion"].unique(), default=df["tipo_operacion"].unique())
filtros = (df["activo"].isin(activo_sel)) & (df["tipo_operacion"].isin(tipo_sel))
df_filtrado = df[filtros]

# ===================== KPIs iniciales =====================
st.title("Cartera de Inversiones")
st.markdown(f"Mostrando datos para **{len(df_filtrado['activo'].unique())} activos**, con tipo de operación: **{', '.join(tipo_sel) if tipo_sel else 'todos'}**")

aporte_total = df_filtrado[df_filtrado["tipo_operacion"] == "aporte"]["importe_euros"].sum()
comisiones_total = df_filtrado[df_filtrado["tipo_operacion"] == "comision"]["importe_euros"].sum()
beneficio_total = df_filtrado[df_filtrado["tipo_operacion"] == "beneficio"]["importe_euros"].sum()
perdidas_total = df_filtrado[df_filtrado["tipo_operacion"].isin(["pérdida", "perdida"])]["importe_euros"].sum()
retirada_total = df_filtrado[df_filtrado["tipo_operacion"] == "retirada"]["importe_euros"].sum()
aporte_neto = aporte_total + retirada_total

# ===================== Calcular valor actual de la cartera =====================
df_flot = df_filtrado[(df_filtrado["tipo_operacion"] == "otro") & (df_filtrado["subtipo_operacion"].isin(["revalorizacion", "devaluacion"]))]
valor_actual = aporte_total + retirada_total + df_flot["importe_euros"].sum()

st.subheader("Valor actual de la cartera")
st.metric("Valor actual estimado", f"{valor_actual:,.2f} €")

# Mostrar KPIs
st.subheader("Resumen de KPIs filtrados")
col1, col2, col3 = st.columns(3)
col1.metric("Total Aportado", f"{aporte_total:.2f} €")
col2.metric("Retirado", f"{retirada_total:.2f} €")
col3.metric("Aporte Neto", f"{aporte_neto:.2f} €")

col4, col5, col6 = st.columns(3)
col4.metric("Beneficios", f"{beneficio_total:.2f} €")
col5.metric("Pérdidas", f"{perdidas_total:.2f} €")
col6.metric("Comisiones", f"{comisiones_total:.2f} €")


# === RENTABILIDAD POR ACTIVO ===
st.subheader("Rentabilidad porcentual por activo")

# Agrupar info
aportes = df_filtrado[df_filtrado["tipo_operacion"].isin(["aporte", "comision"])].groupby("activo")["importe_euros"].sum().reset_index(name="aportado")
retirado = df_filtrado[df_filtrado["tipo_operacion"] == "retirada"].groupby("activo")["importe_euros"].sum().reset_index(name="retirado")
neta = df_filtrado[df_filtrado["tipo_operacion"].isin(["beneficio", "perdida", "perdida"])].groupby("activo")["importe_euros"].sum().reset_index(name="rentabilidad_neta")
flot = df_filtrado[(df_filtrado["tipo_operacion"] == "otro") & (df_filtrado["subtipo_operacion"].isin(["revalorizacion", "devaluacion"]))].groupby("activo")["importe_euros"].sum().reset_index(name="rentabilidad_flotante")

# Consolidar
df_rentabilidad = aportes.merge(retirado, on="activo", how="outer")
df_rentabilidad = df_rentabilidad.merge(neta, on="activo", how="outer")
df_rentabilidad = df_rentabilidad.merge(flot, on="activo", how="outer")
df_rentabilidad = df_rentabilidad.fillna(0)
df_rentabilidad["aporte_neto"] = df_rentabilidad["aportado"] + df_rentabilidad["retirado"]
df_rentabilidad["rentabilidad_total"] = df_rentabilidad["rentabilidad_neta"] + df_rentabilidad["rentabilidad_flotante"]


# Porcentajes
for tipo in ["neta", "flotante", "total"]:
    df_rentabilidad[f"% {tipo}"] = df_rentabilidad.apply(lambda row: (row[f"rentabilidad_{tipo}"] / row["aportado"] * 100) if row["aportado"] != 0 else 0, axis=1)

# Mostrar tabla y gráfica
st.dataframe(df_rentabilidad.sort_values("% total", ascending=False))
fig_bar = go.Figure()
fig_bar.add_bar(x=df_rentabilidad["activo"], y=df_rentabilidad["% neta"], name="% Neta", marker_color="steelblue")
fig_bar.add_bar(x=df_rentabilidad["activo"], y=df_rentabilidad["% flotante"], name="% Flotante", marker_color="gold")
fig_bar.update_layout(title="Rentabilidad porcentual por Activo", barmode="group", yaxis_title="% Rentabilidad")
st.plotly_chart(fig_bar)

# === Rentabilidad acumulada ===
st.subheader("Rentabilidad acumulada (neta vs flotante)")
df_flot = df_filtrado[df_filtrado["subtipo_operacion"].isin(["revalorizacion", "devaluacion"])]
df_net = df_filtrado[df_filtrado["tipo_operacion"].isin(["beneficio", "perdida", "pérdida"])]
df_aport = df_filtrado[df_filtrado["tipo_operacion"].isin(["aporte", "comision"])]

aportado = df_aport.groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="aportado")
neta = df_net.groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="neta")
flotante = df_flot.groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="flotante")

area = aportado.merge(neta, on="fecha", how="outer")
area = area.merge(flotante, on="fecha", how="outer").sort_values("fecha").fillna(method="ffill").fillna(0)
area["% neta"] = area.apply(lambda r: r["neta"] / r["aportado"] * 100 if r["aportado"] > 0 else 0, axis=1)
area["% flotante"] = area.apply(lambda r: r["flotante"] / r["aportado"] * 100 if r["aportado"] > 0 else 0, axis=1)

# % gráfico
fig_pct = go.Figure()
fig_pct.add_trace(go.Scatter(x=area["fecha"], y=area["% flotante"], fill="tozeroy", name="% Rentabilidad Flotante", line=dict(color="gold"), opacity=0.4))
fig_pct.add_trace(go.Scatter(x=area["fecha"], y=area["% neta"], fill="tonexty", name="% Rentabilidad Neta", line=dict(color="steelblue")))
fig_pct.update_layout(xaxis_title="Fecha", yaxis_title="% Rentabilidad")
st.plotly_chart(fig_pct)

# € gráfico
st.subheader("Rentabilidad acumulada en euros")
fig_eur = go.Figure()
fig_eur.add_trace(go.Scatter(x=area["fecha"], y=area["flotante"], fill="tozeroy", name="Rentabilidad Flotante (€)", line=dict(color="gold"), opacity=0.4))
fig_eur.add_trace(go.Scatter(x=area["fecha"], y=area["neta"], fill="tonexty", name="Rentabilidad Neta (€)", line=dict(color="steelblue")))
fig_eur.update_layout(xaxis_title="Fecha", yaxis_title="€ acumulado")
st.plotly_chart(fig_eur)

# === Rentabilidad por año ===
df_filtrado["año"] = df_filtrado["fecha"].dt.year
anual = df_filtrado[df_filtrado["tipo_operacion"].isin(["beneficio", "perdida", "perdida", "otro"])]
anual["importe_euros"] = anual.apply(lambda r: 0 if r["subtipo_operacion"] in ["revalorizacion_final", "devaluacion_final"] else r["importe_euros"], axis=1)

net_anual = anual[anual["tipo_operacion"].isin(["beneficio", "perdida", "perdida"])].groupby("año")["importe_euros"].sum().reset_index(name="rentabilidad_neta")
flot_anual = anual[anual["subtipo_operacion"].isin(["revalorizacion", "devaluacion"])].groupby("año")["importe_euros"].sum().reset_index(name="rentabilidad_flotante")
aport_anual = df_filtrado[df_filtrado["tipo_operacion"].isin(["aporte", "comision"])].groupby("año")["importe_euros"].sum().reset_index(name="aportado")

resumen = net_anual.merge(flot_anual, on="año", how="outer").merge(aport_anual, on="año", how="outer").fillna(0)
resumen["rentabilidad_total"] = resumen["rentabilidad_neta"] + resumen["rentabilidad_flotante"]
resumen["% neta"] = resumen.apply(lambda r: r["rentabilidad_neta"] / r["aportado"] * 100 if r["aportado"] > 0 else 0, axis=1)
resumen["% flotante"] = resumen.apply(lambda r: r["rentabilidad_flotante"] / r["aportado"] * 100 if r["aportado"] > 0 else 0, axis=1)
resumen["% total"] = resumen.apply(lambda r: r["rentabilidad_total"] / r["aportado"] * 100 if r["aportado"] > 0 else 0, axis=1)

st.subheader("Rentabilidad anual por tipo")
st.dataframe(resumen.sort_values("año"))

# === Evolución capital ===
cap = df_filtrado[df_filtrado["tipo_operacion"].isin(["aporte", "comision", "retirada"])]
cap_aport = cap[cap["tipo_operacion"].isin(["aporte", "comision"])].groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="aportado")
cap_retirado = cap[cap["tipo_operacion"] == "retirada"].groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="retirado")

df_capital = pd.merge(cap_aport, cap_retirado, on="fecha", how="outer").fillna(method="ffill").fillna(0).sort_values("fecha")
df_capital["capital_neto"] = df_capital["aportado"] + df_capital["retirado"]

st.subheader("Evolución del capital aportado y retirado")
fig_capital = go.Figure()
fig_capital.add_trace(go.Scatter(x=df_capital["fecha"], y=df_capital["aportado"], name="Capital Aportado", line=dict(color="green")))
fig_capital.add_trace(go.Scatter(x=df_capital["fecha"], y=df_capital["retirado"], name="Capital Retirado", line=dict(color="red")))
fig_capital.add_trace(go.Scatter(x=df_capital["fecha"], y=df_capital["capital_neto"], name="Capital Neto Invertido", line=dict(color="blue", dash="dash")))
fig_capital.update_layout(xaxis_title="Fecha", yaxis_title="€ acumulado")
st.plotly_chart(fig_capital)

# Transacciones
st.subheader("Transacciones filtradas")
st.dataframe(df_filtrado.sort_values("fecha", ascending=False))
