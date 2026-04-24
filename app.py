import streamlit as st
import pandas as pd
from io import BytesIO
import numpy as np
from core.dtype_detector import detect_column_type
from ui.filters_ui import render_filter
from core.rules import apply_rule
from ui.rule_builder import rule_builder

st.set_page_config(page_title="Conciliador de Planillas - IT Concesionaria", layout="wide")

st.title("Conciliador General de Planillas")
st.markdown("Compara dos archivos para encontrar coincidencias, faltantes y diferencias.")

# 1. Carga de Archivos
col1, col2 = st.columns(2)

# Leer archivos
df_a = None
df_b = None

with col1:
    # -------- TABLA A --------
    
    file_a = st.file_uploader("Subir Tabla A (Ej: Administración)", type=['xlsx', 'csv'])
    
    if file_a:
        if file_a.name.endswith("xlsx"):
            excel_a = pd.ExcelFile(file_a)
            sheet_a = st.selectbox(
                "Seleccionar hoja Tabla A",
                excel_a.sheet_names,
                index=excel_a.sheet_names.index(
                    st.session_state.get("sheet_a", excel_a.sheet_names[0])
                ),
                key="sheet_a"
            )

            if len(excel_a.sheet_names) > 1:
                st.caption("📄 Este archivo tiene múltiples hojas")

            df_a = pd.read_excel(file_a, sheet_name=sheet_a)
        else:
            df_a = pd.read_csv(file_a)
            
with col2:

    # -------- TABLA B --------
    file_b = st.file_uploader("Subir Tabla B (Ej: Movimientos)", type=['xlsx', 'csv'])

    if file_b:
        if file_b.name.endswith("xlsx"):
            excel_b = pd.ExcelFile(file_b)
            sheet_b = st.selectbox(
                "Seleccionar hoja Tabla B",
                excel_b.sheet_names,
                index=excel_b.sheet_names.index(
                    st.session_state.get("sheet_b", excel_b.sheet_names[0])
                ),
                key="sheet_b"
            )

            if len(excel_b.sheet_names) > 1:
                st.caption("📄 Este archivo tiene múltiples hojas")

            df_b = pd.read_excel(file_b, sheet_name=sheet_b)
        else:
            df_b = pd.read_csv(file_b)


if df_a is not None and df_b is not None:
    try:        
        col_types = {col: detect_column_type(df_a[col]) for col in df_a.columns}
        
        # Validaciones básicas
        if df_a.empty or df_b.empty:
            st.error("Uno o ambos archivos están vacíos. Por favor, verifica los archivos.")
            st.stop()
        
        if len(df_a.columns) == 0 or len(df_b.columns) == 0:
            st.error("Los archivos deben tener encabezados válidos.")
            st.stop()
            
    except Exception as e:
        st.error(f"Error al leer los archivos: {str(e)}")
        st.stop()

    st.divider()
    with st.expander("ℹ️ ¿Cómo usar los filtros?"):

        st.markdown("""
        ### 🧩 ¿Qué podés hacer acá?

        Podés filtrar la información para encontrar exactamente lo que necesitás.

        No hace falta tener conocimientos técnicos 👍

        ---

        ### 🪜 Paso a paso

        1. Elegí una columna (por ejemplo: Nombre, Fecha, ID)
        2. Elegí una condición (por ejemplo: contiene, mayor que, entre)
        3. Ingresá el valor
        4. Hacé clic en **➕ Agregar regla**

        ---

        ### 🔗 Combinar condiciones

        Podés usar:

        - **Y** → se cumplen TODAS las condiciones  
        (Ej: Nombre contiene "Juan" Y Edad mayor a 30)

        - **O** → se cumple AL MENOS una  
        (Ej: Nombre contiene "Juan" O "Pedro")

        ---

        ### 💡 Ejemplos

        - 🔎 Buscar clientes llamados "Juan"
        - 📅 Ver registros después de cierta fecha
        - 💰 Encontrar montos entre 100 y 500

        ---

        ### ⚠️ Importante

        - Podés modificar las reglas en cualquier momento
        - Si no agregás filtros, se mostrarán todos los datos
        """)

    st.subheader("Filtros avanzados")
    rules, logic = rule_builder(df_a, col_types)

    if not rules:
        st.info("ℹ️ No agregaste filtros. Se analizarán todos los registros.")
    else:
        st.success(f"🔍 Aplicando {len(rules)} filtro(s) con lógica '{logic}'")

    # 2. Configuración de columnas
    col_cfg1, col_cfg2 = st.columns(2)
    
    with col_cfg1:
        key_cols = st.multiselect("Columnas para identificar coincidencias (ID, DNI, etc.)", df_a.columns)
    
    with col_cfg2:
        compare_cols = st.multiselect("Columnas donde querés detectar diferencias", [c for c in df_a.columns if c not in key_cols])

    if st.button("Ejecutar Conciliación") and key_cols:
        # Aplicar reglas antes de conciliar
        if rules:
            mask = None

            for r in rules:
                m = apply_rule(
                    df_a[r["col"]],
                    r["condition"],
                    r.get("value"),
                    r.get("value2"),
                    dtype=col_types[r["col"]]
                )

                if m is None:
                    continue

                if mask is None:
                    mask = m
                else:
                    if logic == "AND":
                        mask = mask & m
                    else:
                        mask = mask | m

            if mask is None:
                st.warning("⚠️ No hay reglas válidas aplicadas.")
            else:
                df_a = df_a[mask]
        
        # Verificar que las columnas de cruce existan en ambas tablas
        missing_in_b = [col for col in key_cols if col not in df_b.columns]
        if missing_in_b:
            st.error(f"Las siguientes columnas de cruce no existen en la Tabla B: {', '.join(missing_in_b)}")
            st.stop()
        
        # --- LÓGICA DE CONCILIACIÓN ---
        try:
            # Realizamos un merge exterior para identificar todo
            df_merge = pd.merge(df_a, df_b, on=key_cols, how='outer', suffixes=('_A', '_B'), indicator=True)

            # Separar resultados
            coincidencias = df_merge[df_merge['_merge'] == 'both'].copy()
            solo_a = df_merge[df_merge['_merge'] == 'left_only'].copy()
            solo_b = df_merge[df_merge['_merge'] == 'right_only'].copy()

            # Detectar diferencias en columnas específicas
            diferencias = pd.DataFrame()
            diferencias_detalle = []
            
            if compare_cols:
                # Verificar que las columnas a comparar existan en ambas tablas
                missing_compare_in_b = [col for col in compare_cols if col not in df_b.columns]
                if missing_compare_in_b:
                    st.warning(f"Las siguientes columnas a comparar no existen en la Tabla B: {', '.join(missing_compare_in_b)}. Se omitirán.")
                    compare_cols = [col for col in compare_cols if col in df_b.columns]
                
                if compare_cols:
                    for idx, row in coincidencias.iterrows():
                        diff_cols = []
                        for col in compare_cols:
                            val_a = row[f"{col}_A"]
                            val_b = row[f"{col}_B"]
                            
                            # Comparar valores considerando NaN
                            if pd.isna(val_a) and pd.isna(val_b):
                                continue
                            elif pd.isna(val_a) or pd.isna(val_b):
                                diff_cols.append(col)
                            elif str(val_a).strip() != str(val_b).strip():
                                diff_cols.append(col)
                        
                        if diff_cols:
                            diferencias_detalle.append({
                                **{col: row[col] for col in key_cols},
                                'Columnas_con_diferencias': ', '.join(diff_cols),
                                **{f"{col}_A": row[f"{col}_A"] for col in diff_cols},
                                **{f"{col}_B": row[f"{col}_B"] for col in diff_cols}
                            })
                    
                    if diferencias_detalle:
                        diferencias = pd.DataFrame(diferencias_detalle)

        except Exception as e:
            st.error(f"Error durante la conciliación: {str(e)}")
            st.stop()

        # 3. Mostrar Resumen en Pantalla
        st.success("Conciliación completada.")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Coincidencias", len(coincidencias))
        m2.metric("Solo en A", len(solo_a))
        m3.metric("Solo en B", len(solo_b))
        m4.metric("Diferencias halladas", len(diferencias))

        # Mostrar preview de resultados
        with st.expander("Vista previa de resultados"):
            tab1, tab2, tab3, tab4 = st.tabs(["Coincidencias", "Solo en A", "Solo en B", "Diferencias"])
            
            with tab1:
                st.dataframe(coincidencias.head(10), use_container_width=True)
            with tab2:
                st.dataframe(solo_a.head(10), use_container_width=True)
            with tab3:
                st.dataframe(solo_b.head(10), use_container_width=True)
            with tab4:
                if not diferencias.empty:
                    st.dataframe(diferencias.head(10), use_container_width=True)
                else:
                    st.info("No se encontraron diferencias en las columnas seleccionadas.")

        # 4. Generar archivo Excel de descarga
        try:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_a.to_excel(writer, index=False, sheet_name='Tabla A Original')
                df_b.to_excel(writer, index=False, sheet_name='Tabla B Original')
                coincidencias.drop(columns=['_merge'], errors='ignore').to_excel(writer, index=False, sheet_name='Coincidencias')
                solo_a.drop(columns=['_merge'], errors='ignore').to_excel(writer, index=False, sheet_name='Solo en A')
                solo_b.drop(columns=['_merge'], errors='ignore').to_excel(writer, index=False, sheet_name='Solo en B')
                if not diferencias.empty:
                    diferencias.to_excel(writer, index=False, sheet_name='Diferencias')

            st.download_button(
                label="📥 Descargar Reporte de Conciliación",
                data=output.getvalue(),
                file_name="conciliacion_resultado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Error al generar el archivo de descarga: {str(e)}")
            
else:
    st.info("Por favor, sube ambos archivos para comenzar.")