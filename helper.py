from datetime import datetime
import math
import pandas as pd
from typing import List, Tuple

# === XIRR ===
def xirr(cashflows: List[Tuple[datetime, float]], guess: float = 0.1, max_iterations: int = 100, tol: float = 1e-6):
    cashflows = sorted(cashflows, key=lambda x: x[0])
    if len(cashflows) < 2:
        return None

    days = [(cf[0] - cashflows[0][0]).days for cf in cashflows]
    values = [cf[1] for cf in cashflows]

    def f(rate):
        try:
            return sum([v / ((1 + rate) ** (d / 365.0)) for v, d in zip(values, days)])
        except Exception:
            return float('nan')

    def f_derivative(rate):
        try:
            return sum([- (d / 365.0) * v / ((1 + rate) ** ((d / 365.0) + 1)) for v, d in zip(values, days)])
        except Exception:
            return float('nan')

    rate = guess
    for _ in range(max_iterations):
        if rate <= -0.999:
            return None

        f_val, f_deriv = f(rate), f_derivative(rate)
        if math.isnan(f_val) or math.isnan(f_deriv) or abs(f_deriv) < 1e-10:
            return None

        new_rate = rate - f_val / f_deriv
        if abs(new_rate - rate) < tol:
            return new_rate
        rate = new_rate

    return None


# === UTILIDADES COMPARTIDAS ===
def filtrar_flujos_validos(df):
    return df[
        df["tipo_operacion"].isin(["aporte", "comision", "retirada"]) &
        ~((df["tipo_operacion"] == "aporte") & df["subtipo_operacion"].str.startswith("reinv")) &
        ~((df["tipo_operacion"] == "retirada") & (df["subtipo_operacion"] == "ajuste_por_perdida"))
    ]

def obtener_cashflows(df):
    return df.apply(
        lambda r: (
            r["fecha_hora"].to_pydatetime(),
            -r["importe_euros"]
        ), axis=1
    ).tolist()

def obtener_flotante(df):
    return df[(df["tipo_operacion"] == "otro") & (df["subtipo_operacion"].isin(["revalorizacion", "devaluacion"]))]["importe_euros"].sum()


# === FUNCIONES ===
def calcular_rentabilidad_por_activo(df):
    resultados = []
    for activo in df["activo"].dropna().unique():
        sub = df[df["activo"] == activo]

        aporte_compras = sub[(sub["tipo_operacion"] == "aporte") & (sub["subtipo_operacion"] == "compra")]["importe_euros"].sum()
        retiradas = sub[(sub["tipo_operacion"] == "retirada") & (sub["subtipo_operacion"] == "retirada")]["importe_euros"].sum()
        aporte_reinv = sub[(sub["tipo_operacion"] == "aporte") & (sub["subtipo_operacion"].str.startswith("reinv"))]["importe_euros"].sum()
        ajuste_perdida = sub[(sub["tipo_operacion"] == "retirada") & (sub["subtipo_operacion"] == "ajuste_por_perdida")]["importe_euros"].sum()

        aportado = aporte_compras + retiradas
        aporte_neto = aportado + aporte_reinv + ajuste_perdida

        beneficio_consolidado = sub[sub["tipo_operacion"].isin(["beneficio", "perdida"])]["importe_euros"].sum()
        beneficio_flotante = obtener_flotante(sub)
        valor_actual = aporte_neto + beneficio_flotante
        beneficio_total = beneficio_consolidado + beneficio_flotante
        rentabilidad_pct = (beneficio_total / aportado) * 100 if aportado != 0 else None

        tir = calcular_tir_desde_df(sub, valor_actual)

        resultados.append({
            "activo": activo,
            "aportado": aportado,
            "beneficio_consolidado": beneficio_consolidado,
            "valor_flotante": beneficio_flotante,
            "beneficio_neto": beneficio_total,
            "valor_actual": valor_actual,
            "% rentabilidad_total": rentabilidad_pct,
            "TIR %": tir * 100 if tir is not None else None,
            "n_aportes": sub[(sub["tipo_operacion"] == "aporte") & (~sub["subtipo_operacion"].str.startswith("reinv"))].shape[0],
            "primera_fecha": sub["fecha_hora"].min(),
            "última_fecha": sub["fecha_hora"].max()
        })
    return pd.DataFrame(resultados)

def calcular_rentabilidad_anual(df):
    df = df.copy()
    df["año"] = df["fecha_hora"].dt.year
    df["subtipo_operacion"] = df["subtipo_operacion"].fillna("")

    aportado = df[df["tipo_operacion"].isin(["aporte", "comision"])].groupby("año")["importe_euros"].sum().reset_index(name="aportado")
    consolidado = df[df["tipo_operacion"].isin(["beneficio", "perdida"])].groupby("año")["importe_euros"].sum().reset_index(name="beneficio_consolidado")
    flotante = df[(df["tipo_operacion"] == "otro") & (df["subtipo_operacion"].isin(["revalorizacion", "devaluacion"]))].groupby("año")["importe_euros"].sum().reset_index(name="beneficio_flotante")

    df_anual = aportado.merge(consolidado, on="año", how="outer").merge(flotante, on="año", how="outer").fillna(0)
    df_anual["beneficio_total"] = df_anual["beneficio_consolidado"] + df_anual["beneficio_flotante"]
    df_anual["% rentabilidad total"] = df_anual.apply(lambda r: (r["beneficio_total"] / r["aportado"] * 100) if r["aportado"] != 0 else None, axis=1)
    df_anual["% consolidado"] = df_anual.apply(lambda r: (r["beneficio_consolidado"] / r["aportado"] * 100) if r["aportado"] != 0 else None, axis=1)
    df_anual["% flotante"] = df_anual.apply(lambda r: (r["beneficio_flotante"] / r["aportado"] * 100) if r["aportado"] != 0 else None, axis=1)

    return df_anual.sort_values("año")

def calcular_tir_desde_df(df, valor_actual):
    flujos_validos = filtrar_flujos_validos(df)
    if flujos_validos.empty:
        return None
    cashflows = obtener_cashflows(flujos_validos)
    if not cashflows:
        return None
    fecha_final = df["fecha_hora"].max().to_pydatetime()
    cashflows.append((fecha_final, valor_actual))
    return xirr(cashflows)

def calcular_tir_acumulado_en_tiempo(df, frecuencia="W"):
    if df.empty or df["fecha_hora"].isna().all():
        return pd.DataFrame()

    fechas = pd.date_range(start=df["fecha_hora"].min(), end=df["fecha_hora"].max(), freq=frecuencia)
    resultado = []

    for fecha_corte in fechas:
        df_corte = df[df["fecha_hora"] <= fecha_corte]
        flujos_validos = filtrar_flujos_validos(df_corte)
        cashflows = obtener_cashflows(flujos_validos)

        valor_estimado = flujos_validos["importe_euros"].sum() + obtener_flotante(df_corte)

        tir_pct = None
        if len(cashflows) > 0:
            cashflows.append((fecha_corte.to_pydatetime(), valor_estimado))
            try:
                tir = xirr(cashflows)
                tir_pct = tir * 100 if tir is not None else None
            except Exception:
                pass

        resultado.append({"fecha": fecha_corte, "TIR %": tir_pct})

    return pd.DataFrame(resultado)

def calcular_tir_anual(df, xirr_func):
    df = df.copy()
    df["año"] = df["fecha_hora"].dt.year
    df["subtipo_operacion"] = df["subtipo_operacion"].fillna("")

    resultado = []
    for año in sorted(df["año"].unique()):
        df_año = df[df["año"] == año]
        flujos = filtrar_flujos_validos(df_año)
        cashflows = obtener_cashflows(flujos)
        valor_estimado = flujos["importe_euros"].sum() + obtener_flotante(df_año)

        tir_pct = None
        if len(cashflows) > 0:
            cashflows.append((datetime(año, 12, 31), valor_estimado))
            try:
                tir = xirr_func(cashflows)
                tir_pct = tir * 100 if tir is not None else None
            except Exception:
                pass

        resultado.append({"año": año, "TIR %": tir_pct})

    return pd.DataFrame(resultado)