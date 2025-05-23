import pandas as pd

def detectar_retiradas_con_beneficio_oculto(df, umbral=50):
    """
    Identifica retiradas que podrían haber generado un beneficio no registrado.

    Params:
        df: DataFrame completo de transacciones.
        umbral: importe mínimo retirado para considerar relevante.

    Returns:
        DataFrame con candidatos a beneficio no registrado.
    """
    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    
    # Filtrar retiradas significativas
    retiradas = df[(df["tipo_operacion"] == "retirada") & (df["importe"] < -umbral)]

    resultados = []
    for _, row in retiradas.iterrows():
        activo = row["activo"]
        fecha = row["fecha"]
        importe_retirado = row["importe"]
        
        # ¿Había aportes previos?
        aportes_anteriores = df[(df["activo"] == activo) & 
                                (df["tipo_operacion"] == "aporte") & 
                                (df["fecha"] < fecha)]
        if aportes_anteriores.empty:
            continue
        
        total_aportado = aportes_anteriores["importe"].sum()

        # ¿Ya hay beneficio registrado en esa fecha?
        hay_beneficio = not df[(df["activo"] == activo) &
                               (df["fecha"] == fecha) &
                               (df["tipo_operacion"] == "beneficio")].empty
        if hay_beneficio:
            continue
        
        # ¿Hubo un nuevo aporte cercano en el tiempo?
        aporte_post = df[(df["activo"] == activo) &
                         (df["tipo_operacion"] == "aporte") &
                         (df["fecha"] >= fecha)]

        beneficio_estimado = abs(importe_retirado) - total_aportado
        if beneficio_estimado > 0:
            resultados.append({
                "activo": activo,
                "fecha": fecha.date(),
                "retirado": importe_retirado,
                "aportado_previo": total_aportado,
                "beneficio_estimado": round(beneficio_estimado, 2),
                "reinversion_detectada": not aporte_post.empty
            })

    return pd.DataFrame(resultados)

# === EJEMPLO DE USO ===
if __name__ == "__main__":
    # Cargar desde tu Excel si es necesario
    df = pd.read_excel("transacciones.xlsx")

    df_resultados = detectar_retiradas_con_beneficio_oculto(df)

    # Guardar sugerencias o mostrarlas
    df_resultados.to_excel("posibles_beneficios_no_registrados.xlsx", index=False)
    print(df_resultados)
