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


###############
# Aporte bruto por compras
aporte_compras = df_filtrado[(df_filtrado["tipo_operacion"] == "aporte") & (df_filtrado["subtipo_operacion"] == "compra")]["importe_euros"].sum()
retiradas_puras = df_filtrado[(df_filtrado["tipo_operacion"] == "retirada") & (df_filtrado["subtipo_operacion"] == "retirada")]["importe_euros"].sum()
aporte_bruto_compras = aporte_compras + retiradas_puras

# Aporte bruto por reinversión neto = reinv - ajuste_por_perdida
aporte_reinv = df_filtrado[(df_filtrado["tipo_operacion"] == "aporte") & (df_filtrado["subtipo_operacion"].str.startswith("reinv"))]["importe_euros"].sum()
ajuste_perdida = df_filtrado[(df_filtrado["tipo_operacion"] == "retirada") & (df_filtrado["subtipo_operacion"] == "ajuste_por_perdida")]["importe_euros"].sum()
aporte_bruto_reinv = aporte_reinv + ajuste_perdida

# Aporte neto
aporte_neto = aporte_bruto_compras + aporte_bruto_reinv


# Beneficio bruto
beneficios = df_filtrado[df_filtrado["tipo_operacion"] == "beneficio"]["importe_euros"].sum()
perdidas = df_filtrado[df_filtrado["tipo_operacion"] == "perdida"]["importe_euros"].sum()
beneficio_bruto = beneficios + perdidas

# Beneficio flotante
beneficios_flotantes = df_filtrado[(df_filtrado["tipo_operacion"] == "otro") & (df_filtrado["subtipo_operacion"].isin(["revalorizacion", "devaluacion"]))]["importe_euros"].sum()

# Beneficio neto
beneficio_neto = beneficio_bruto + beneficios_flotantes

# Comisiones
comisiones_total = df_filtrado[df_filtrado["tipo_operacion"] == "comision"]["importe_euros"].sum()


# Rentabilidades
def calcular_rentabilidad(valor_final, aporte):
    if aporte > 0:
        return (valor_final / aporte - 1) * 100
    elif aporte <= 0 and valor_final < 0:
        return (valor_final - aporte) / abs(aporte) * 100
    elif aporte <= 0 and valor_final >= 0:
        return float('inf')  # podría mostrarse como '∞' o 'N/A' en frontend
    else:
        return 0

# Rentabilidad consolidada: no usar la función
rentabilidad_consolidada_sin_reinversion = (beneficio_bruto / aporte_bruto_compras) * 100 if aporte_bruto_compras != 0 else 0
rentabilidad_consolidada_con_reinversion = (beneficio_bruto / aporte_neto) * 100 if aporte_neto != 0 else 0

# Rentabilidad total: sí usar función
valor_actual = aporte_neto + beneficios_flotantes
valor_actual_sin_reinv = aporte_bruto_compras + beneficio_bruto + beneficios_flotantes

print(" VALOR ACTUAL: ", valor_actual)
print(" APORTE NETO: ", aporte_neto)
rentabilidad_total_sin_reinversion = calcular_rentabilidad(valor_actual_sin_reinv, aporte_bruto_compras)
rentabilidad_total_con_reinversion = calcular_rentabilidad(valor_actual, aporte_neto)

###############

# ===================== Calcular valor actual de la cartera =====================
#df_flot = df_filtrado[(df_filtrado["tipo_operacion"] == "otro") & (df_filtrado["subtipo_operacion"].isin(["revalorizacion", "devaluacion"]))]


st.subheader("Valor actual de la cartera")
st.metric("Valor actual estimado", f"{valor_actual:,.2f} €")

# Mostrar KPIs
st.subheader("Resumen de KPIs filtrados")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Aporte Bruto", f"{aporte_bruto_compras:.2f} €")
col2.metric("Aporte Reinv - Pér", f"{aporte_bruto_reinv:.2f} €")
col3.metric("Aporte Neto", f"{aporte_neto:.2f} €")
col4.metric("Comisiones", f"{comisiones_total:.2f} €")

col5, col6, col7 = st.columns(3)
col5.metric("Beneficio Consolidado", f"{beneficio_bruto:.2f} €")
col6.metric("Beneficio Flotante", f"{beneficios_flotantes:.2f} €")
col7.metric("Beneficio Neto", f"{beneficio_neto:.2f} €")

col8, col9, col10, col11 = st.columns(4)
col8.metric("Rent. Cons. (sin reinversión)", f"{rentabilidad_consolidada_sin_reinversion:.2f} %")
col9.metric("Rent. Cons. (con reinversión)", f"{rentabilidad_consolidada_con_reinversion:.2f} %")
col10.metric("Rent. Total (sin reinversión)", f"{rentabilidad_total_sin_reinversion:.2f} %")
col11.metric("Rent. Total (con reinversión)", f"{rentabilidad_total_con_reinversion:.2f} %")



# === Tabla de KPIs por activo ===
st.subheader("KPIs por Activo")

resumen = []

for activo, grupo in df_filtrado.groupby("activo"):
    aporte_compras = grupo[(grupo["tipo_operacion"] == "aporte") & (grupo["subtipo_operacion"] == "compra")]["importe_euros"].sum()
    retiradas_puras = grupo[(grupo["tipo_operacion"] == "retirada") & (grupo["subtipo_operacion"] == "retirada")]["importe_euros"].sum()
    aporte_bruto_compras = aporte_compras + retiradas_puras

    aporte_reinv = grupo[(grupo["tipo_operacion"] == "aporte") & (grupo["subtipo_operacion"].str.startswith("reinv"))]["importe_euros"].sum()
    ajuste_perdida = grupo[(grupo["tipo_operacion"] == "retirada") & (grupo["subtipo_operacion"] == "ajuste_por_perdida")]["importe_euros"].sum()
    aporte_bruto_reinv = aporte_reinv + ajuste_perdida

    aporte_neto = aporte_bruto_compras + aporte_bruto_reinv

    beneficios = grupo[grupo["tipo_operacion"] == "beneficio"]["importe_euros"].sum()
    perdidas = grupo[grupo["tipo_operacion"].isin(["perdida", "pérdida"])]["importe_euros"].sum()
    beneficio_bruto = beneficios + perdidas

    beneficios_flotantes = grupo[
        (grupo["tipo_operacion"] == "otro") &
        (grupo["subtipo_operacion"].isin(["revalorizacion", "devaluacion"]))
    ]["importe_euros"].sum()
    beneficio_neto = beneficio_bruto + beneficios_flotantes

    valor_actual = aporte_neto + beneficios_flotantes

    r1 = calcular_rentabilidad(beneficio_bruto, aporte_bruto_compras)
    r2 = calcular_rentabilidad(beneficio_bruto, aporte_neto)
    r3 = calcular_rentabilidad(beneficio_neto, aporte_bruto_compras)
    r4 = calcular_rentabilidad(beneficio_neto, aporte_neto)

    resumen.append({
        "Activo": activo,
        "Valor actual": valor_actual,
        "Aporte bruto": aporte_bruto_compras,
        "Aporte neto": aporte_neto,
        "Ben/Pér Brutos": beneficio_bruto,
        "Ben/Pér Netos": beneficio_neto,
        "Rent. cons. (sin reinv) %": r1,
        "Rent. cons. (con reinv) %": r2,
        "Rent. total (sin reinv) %": r3,
        "Rent. total (con reinv) %": r4,
    })

df_resumen = pd.DataFrame(resumen)

# Fila TOTAL
tot = df_resumen[["Valor actual", "Aporte bruto", "Aporte neto", "Ben/Pér Brutos", "Ben/Pér Netos"]].sum()
r1 = calcular_rentabilidad(tot["Ben/Pér Brutos"], tot["Aporte bruto"])
r2 = calcular_rentabilidad(tot["Ben/Pér Brutos"], tot["Aporte neto"])
r3 = calcular_rentabilidad(tot["Ben/Pér Netos"], tot["Aporte bruto"])
r4 = calcular_rentabilidad(tot["Ben/Pér Netos"], tot["Aporte neto"])


df_resumen.loc[len(df_resumen)] = {
    "Activo": "TOTAL",
    "Valor actual": tot["Valor actual"],
    "Aporte bruto": tot["Aporte bruto"],
    "Aporte neto": tot["Aporte neto"],
    "Ben/Pér Brutos": tot["Ben/Pér Brutos"],
    "Ben/Pér Netos": tot["Ben/Pér Netos"],
    "Rent. cons. (sin reinv) %": r1,
    "Rent. cons. (con reinv) %": r2,
    "Rent. total (sin reinv) %": r3,
    "Rent. total (con reinv) %": r4,
}

# Mostrar tabla con formato
st.dataframe(df_resumen.style.format({
    "Valor actual": "{:,.2f} €",
    "Aporte bruto": "{:,.2f} €",
    "Aporte neto": "{:,.2f} €",
    "Ben/Pér Brutos": "{:,.2f} €",
    "Ben/Pér Netos": "{:,.2f} €",
    "Rent. cons. (sin reinv) %": "{:.2f} %",
    "Rent. cons. (con reinv) %": "{:.2f} %",
    "Rent. total (sin reinv) %": "{:.2f} %",
    "Rent. total (con reinv) %": "{:.2f} %",
}))







# === Rentabilidad acumulada: consolidada vs total (ambas con reinversión) ===
st.subheader("Evolución de Rentabilidad (con reinversión)")

MIN_APORTE = 100  # Umbral mínimo para evitar distorsión

# Aportes netos con reinversión
df_aportes_netos = df_filtrado[
    (df_filtrado["tipo_operacion"] == "aporte") &
    (df_filtrado["subtipo_operacion"].isin(["compra", "reinv_benef", "reinv_cashback", "reinv_recom"]))
].groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="aportado")

ajuste_perdidas = df_filtrado[
    (df_filtrado["tipo_operacion"] == "retirada") &
    (df_filtrado["subtipo_operacion"] == "ajuste_por_perdida")
].groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="ajuste_por_perdida")

aporte_neto = pd.merge(df_aportes_netos, ajuste_perdidas, on="fecha", how="outer").sort_values("fecha").fillna(0)
aporte_neto["aportado_neto"] = aporte_neto["aportado"] + aporte_neto["ajuste_por_perdida"]  # ajuste ya es negativo

# Beneficio bruto acumulado
beneficios_consol = df_filtrado[df_filtrado["tipo_operacion"].isin(["beneficio", "perdida", "pérdida"])]
beneficio_bruto = beneficios_consol.groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="beneficio_bruto")

# Beneficio flotante acumulado
beneficios_flot = df_filtrado[
    (df_filtrado["tipo_operacion"] == "otro") &
    (df_filtrado["subtipo_operacion"].isin(["revalorizacion", "devaluacion"]))
].groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="beneficio_flotante")

# Unir todo
rent_df = pd.merge(aporte_neto, beneficio_bruto, on="fecha", how="outer")
rent_df = pd.merge(rent_df, beneficios_flot, on="fecha", how="outer").sort_values("fecha").fillna(method="ffill").fillna(0)

# Calcular valor de cartera
rent_df["valor_cartera"] = rent_df["aportado_neto"] + rent_df["beneficio_flotante"]

# Rentabilidades acumuladas con filtro por mínimo aporte
rent_df["rentabilidad_consolidada"] = rent_df.apply(
    lambda r: r["beneficio_bruto"] / r["aportado_neto"] * 100 if r["aportado_neto"] > MIN_APORTE else None,
    axis=1
)

rent_df["rentabilidad_total"] = rent_df.apply(
    lambda r: (r["valor_cartera"] / r["aportado_neto"] - 1) * 100 if r["aportado_neto"] > MIN_APORTE else None,
    axis=1
)

# === Gráficos
col1, col2 = st.columns(2)

with col1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rent_df["fecha"], y=rent_df["rentabilidad_consolidada"], fill="tozeroy",
        name="% Rentabilidad Consolidada (con reinv.)", line=dict(color="steelblue")
    ))
    fig.add_trace(go.Scatter(
        x=rent_df["fecha"], y=rent_df["rentabilidad_total"], fill="tonexty",
        name="% Rentabilidad Total (con reinv.)", line=dict(color="gold"), opacity=0.4
    ))

    fig.update_layout(
        title="Rentabilidad acumulada (con reinversión)",
        xaxis_title="Fecha",
        yaxis_title="% Rentabilidad",
        legend=dict(x=0, y=1.1, orientation="h")
    )

    st.plotly_chart(fig, use_container_width=True, key="rentabilidad_pct")

with col2:
    fig_euros = go.Figure()
    fig_euros.add_trace(go.Scatter(
        x=rent_df["fecha"], y=rent_df["beneficio_bruto"], fill="tozeroy",
        name="Beneficio Bruto (€)", line=dict(color="steelblue")
    ))
    fig_euros.add_trace(go.Scatter(
        x=rent_df["fecha"], y=rent_df["beneficio_bruto"] + rent_df["beneficio_flotante"],
        fill="tonexty", name="Beneficio Neto (€)", line=dict(color="gold"), opacity=0.4
    ))
    fig_euros.update_layout(
        title="Evolución del Beneficio (€)",
        xaxis_title="Fecha",
        yaxis_title="€ acumulado",
        legend=dict(x=0, y=1.1, orientation="h")
    )
    st.plotly_chart(fig_euros, use_container_width=True, key="rentabilidad_eur")








# === Rentabilidad Comp. Anual (CAGR) ===
st.subheader("Rentabilidad Compuesta Anual (CAGR)")

# Preparar datos
resumen_anual = []
df["año"] = df["fecha"].dt.year
primer_año = df["año"].min()
ultimo_año = df["año"].max()

for año in sorted(df["año"].unique()):
    grupo = df[df["año"] <= año]

    # Aportes acumulados
    aporte_total = grupo[
        (grupo["tipo_operacion"].isin(["aporte", "retirada"])) &
        (grupo["subtipo_operacion"].isin(["compra", "reinv_benef", "reinv_cashback", "reinv_recom", "retirada", "ajuste_por_perdida"]))
    ]["importe_euros"].sum()

    # Beneficio flotante
    beneficio_flotante = grupo[
        (grupo["tipo_operacion"] == "otro") &
        (grupo["subtipo_operacion"].isin(["revalorizacion", "devaluacion"]))
    ]["importe_euros"].sum()

    # Beneficio consolidado
    beneficio_bruto = grupo[
        grupo["tipo_operacion"].isin(["beneficio", "perdida", "pérdida"])
    ]["importe_euros"].sum()

    beneficio_neto = beneficio_bruto + beneficio_flotante
    valor_cartera = aporte_total + beneficio_flotante

    años_transcurridos = año - primer_año + 1

    # Rentabilidades compuestas
    cagr_bruto = ((1 + (beneficio_bruto / aporte_total)) ** (1 / años_transcurridos) - 1) * 100 if aporte_total > 0 else 0
    cagr_neto = ((1 + (beneficio_neto / aporte_total)) ** (1 / años_transcurridos) - 1) * 100 if aporte_total > 0 else 0

    resumen_anual.append({
        "año": año,
        "Valor cartera": valor_cartera,
        "Aporte neto acumulado": aporte_total,
        "Ben/Pér Brutos acumulado": beneficio_bruto,
        "Ben/Pér Netos acumulado": beneficio_neto,
        "CAGR consolidado %": cagr_bruto,
        "CAGR total %": cagr_neto,
    })

df_cagr = pd.DataFrame(resumen_anual)

# === Calcular CAGR total para la última fila
aporte_total = df_cagr["Aporte neto acumulado"].iloc[-1]
valor_final = df_cagr["Valor cartera"].iloc[-1]
n_total = ultimo_año - primer_año + 1

cagr_total = ((valor_final / aporte_total) ** (1 / n_total) - 1) * 100 if aporte_total > 0 else 0

df_cagr.loc[len(df_cagr)] = {
    "año": "CAGR TOTAL",
    "Valor cartera": valor_final,
    "Aporte neto acumulado": aporte_total,
    "Ben/Pér Brutos acumulado": df_cagr["Ben/Pér Brutos acumulado"].iloc[-1],
    "Ben/Pér Netos acumulado": df_cagr["Ben/Pér Netos acumulado"].iloc[-1],
    "CAGR consolidado %": cagr_total,
    "CAGR total %": cagr_total,
}

# Mostrar tabla con formato
st.dataframe(df_cagr.style.format({
    "Valor cartera": "{:,.2f} €",
    "Aporte neto acumulado": "{:,.2f} €",
    "Ben/Pér Brutos acumulado": "{:,.2f} €",
    "Ben/Pér Netos acumulado": "{:,.2f} €",
    "CAGR consolidado %": "{:.2f} %",
    "CAGR total %": "{:.2f} %",
}))








# === Evolución del Dinero Aportado y Valor de la Cartera ===
st.subheader("Evolución del Dinero Aportado y Valor de la Cartera")

# Aportes por compra
aportes_compra = df[
    (df["tipo_operacion"] == "aporte") & 
    (df["subtipo_operacion"] == "compra")
].groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="aporte_bruto")

# Aportes por reinversión
aportes_reinv = df[
    (df["tipo_operacion"] == "aporte") &
    (df["subtipo_operacion"].str.startswith("reinv"))
].groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="aporte_reinv")

# Ajustes por pérdida (ya son negativos)
ajustes_perdida = df[
    (df["tipo_operacion"] == "retirada") & 
    (df["subtipo_operacion"] == "ajuste_por_perdida")
].groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="ajuste_perdida")

# Reinv neto = reinv + ajuste
reinv_neto = pd.merge(aportes_reinv, ajustes_perdida, on="fecha", how="outer").sort_values("fecha").fillna(0)
reinv_neto["aporte_reinv_neto"] = reinv_neto["aporte_reinv"] + reinv_neto["ajuste_perdida"]
reinv_neto = reinv_neto[["fecha", "aporte_reinv_neto"]].fillna(method="ffill")

# Beneficio flotante (revalorizaciones)
flotante = df[
    (df["tipo_operacion"] == "otro") & 
    (df["subtipo_operacion"].isin(["revalorizacion", "devaluacion"]))
].groupby("fecha")["importe_euros"].sum().cumsum().reset_index(name="beneficio_flotante")

# Consolidar aportes
df_aportes = pd.merge(aportes_compra, reinv_neto, on="fecha", how="outer").sort_values("fecha")
df_aportes = df_aportes.fillna(method="ffill").fillna(0)
df_aportes["aporte_neto"] = df_aportes["aporte_bruto"] + df_aportes["aporte_reinv_neto"]

# Valor de la cartera = aporte_neto + beneficio_flotante
df_aportes = pd.merge(df_aportes, flotante, on="fecha", how="outer").sort_values("fecha").fillna(method="ffill").fillna(0)
df_aportes["valor_cartera"] = df_aportes["aporte_neto"] + df_aportes["beneficio_flotante"]

# === Gráfico
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_aportes["fecha"], y=df_aportes["aporte_bruto"],
    name="Aporte Bruto (compras)", line=dict(color="blue")
))
fig.add_trace(go.Scatter(
    x=df_aportes["fecha"], y=df_aportes["aporte_reinv_neto"],
    name="Aporte Reinv - Pér", line=dict(color="orange")
))
fig.add_trace(go.Scatter(
    x=df_aportes["fecha"], y=df_aportes["aporte_neto"],
    name="Aporte Neto Total", line=dict(color="green")
))
fig.add_trace(go.Scatter(
    x=df_aportes["fecha"], y=df_aportes["valor_cartera"],
    name="Valor de la Cartera", line=dict(color="red", dash="dash")
))

fig.update_layout(
    title="Evolución del Aporte de Capital y Valor de la Cartera",
    xaxis_title="Fecha",
    yaxis_title="€ acumulado",
    legend=dict(x=0, y=1.1, orientation="h"),
    height=500
)

st.plotly_chart(fig, use_container_width=True)






# Transacciones
st.subheader("Transacciones filtradas")
st.dataframe(df_filtrado.sort_values("fecha", ascending=False))
