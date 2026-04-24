import logging
from io import BytesIO

import pandas as pd
import streamlit as st

from core.comparator import conciliar
from core.dtype_detector import detect_column_type, VALID_TYPES
from core.rules import apply_rule
from ui.rule_builder import rule_builder
from utils.file_loader import accepted_extensions, get_excel_sheets, load_dataframe

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="Conciliador de Planillas - IT Concesionaria", layout="wide")

st.title("Conciliador General de Planillas")
st.markdown("Compara dos archivos para encontrar coincidencias, faltantes y diferencias.")

# ── Carga de archivos ──────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
df_a = None
df_b = None
ext = accepted_extensions()

with col1:
    file_a = st.file_uploader("Subir Tabla A (Ej: Administración)", type=ext)
    if file_a:
        sheet_a = None
        if file_a.name.lower().endswith((".xlsx", ".xls", ".xlsm", ".xlsb")):
            sheets_a = get_excel_sheets(file_a.getvalue(), file_a.name)
            sheet_a = st.selectbox("Seleccionar hoja Tabla A", sheets_a, key="sheet_a")
            if len(sheets_a) > 1:
                st.caption("📄 Este archivo tiene múltiples hojas")
        df_a = load_dataframe(file_a.getvalue(), file_a.name, sheet=sheet_a)

with col2:
    file_b = st.file_uploader("Subir Tabla B (Ej: Movimientos)", type=ext)
    if file_b:
        sheet_b = None
        if file_b.name.lower().endswith((".xlsx", ".xls", ".xlsm", ".xlsb")):
            sheets_b = get_excel_sheets(file_b.getvalue(), file_b.name)
            sheet_b = st.selectbox("Seleccionar hoja Tabla B", sheets_b, key="sheet_b")
            if len(sheets_b) > 1:
                st.caption("📄 Este archivo tiene múltiples hojas")
        df_b = load_dataframe(file_b.getvalue(), file_b.name, sheet=sheet_b)


if df_a is not None and df_b is not None:

    # Validación temprana
    if df_a.empty or df_b.empty:
        st.error("Uno o ambos archivos están vacíos. Por favor, verifica los archivos.")
        st.stop()
    if len(df_a.columns) == 0 or len(df_b.columns) == 0:
        st.error("Los archivos deben tener encabezados válidos.")
        st.stop()

    # ── Detección de tipos ─────────────────────────────────────────────────────
    try:
        detected_types = {col: detect_column_type(df_a[col]) for col in df_a.columns}
    except Exception:
        logger.exception("Error al detectar tipos de columnas")
        st.error("Error al analizar las columnas del archivo.")
        st.stop()

    # ── Override manual de tipos ───────────────────────────────────────────────
    with st.expander("🔧 Corregir tipos de datos detectados (opcional)"):
        st.caption(
            "Si el tipo detectado es incorrecto (ej: un código fue tomado como fecha), "
            "podés corregirlo acá antes de aplicar filtros."
        )

        type_labels = {"str": "Texto", "int": "Número entero", "float": "Número decimal", "date": "Fecha"}
        cols_per_row = 4
        col_list = list(df_a.columns)

        # Inicializar overrides en session_state cuando cambia el archivo
        file_key = (file_a.name if file_a else "") + (file_b.name if file_b else "")
        if st.session_state.get("_type_override_file_key") != file_key:
            st.session_state["_type_override_file_key"] = file_key
            st.session_state["col_type_overrides"] = dict(detected_types)

        overrides = st.session_state["col_type_overrides"]

        for i in range(0, len(col_list), cols_per_row):
            row_cols = col_list[i:i + cols_per_row]
            ui_cols = st.columns(cols_per_row)
            for j, col_name in enumerate(row_cols):
                with ui_cols[j]:
                    current = overrides.get(col_name, detected_types[col_name])
                    detected_label = f"🤖 {type_labels[detected_types[col_name]]}"
                    options = VALID_TYPES
                    new_type = st.selectbox(
                        f"**{col_name}**",
                        options,
                        index=options.index(current),
                        format_func=lambda t: f"{type_labels[t]} {'✏️' if t != detected_types.get(col_name) else ''}",
                        key=f"type_override_{col_name}",
                        help=f"Detectado automáticamente: {detected_label}"
                    )
                    overrides[col_name] = new_type

        col_types = overrides

    st.divider()

    # ── Ayuda y filtros ────────────────────────────────────────────────────────
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

    # ── Configuración de columnas ──────────────────────────────────────────────
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        key_cols = st.multiselect("Columnas para identificar coincidencias (ID, DNI, etc.)", df_a.columns)
    with col_cfg2:
        compare_cols = st.multiselect(
            "Columnas donde querés detectar diferencias",
            [c for c in df_a.columns if c not in key_cols]
        )

    if st.button("Ejecutar Conciliación") and key_cols:

        # Aplicar filtros
        if rules:
            mask = None
            for r in rules:
                m = apply_rule(
                    df_a[r["col"]], r["condition"],
                    r.get("value"), r.get("value2"),
                    dtype=col_types[r["col"]]
                )
                if m is None:
                    continue
                mask = m if mask is None else (mask & m if logic == "AND" else mask | m)

            if mask is None:
                st.warning("⚠️ No hay reglas válidas aplicadas.")
            else:
                df_a = df_a[mask]

        # Validar columnas de cruce en Tabla B
        missing_in_b = [col for col in key_cols if col not in df_b.columns]
        if missing_in_b:
            st.error(f"Las siguientes columnas no existen en Tabla B: {', '.join(missing_in_b)}")
            st.stop()

        # Validar columnas de comparación en Tabla B
        missing_compare = [col for col in compare_cols if col not in df_b.columns]
        if missing_compare:
            st.warning(f"Columnas ignoradas (no están en Tabla B): {', '.join(missing_compare)}")
            compare_cols = [col for col in compare_cols if col in df_b.columns]

        # Conciliar
        try:
            coincidencias, solo_a, solo_b, diferencias = conciliar(df_a, df_b, key_cols, compare_cols)
        except Exception:
            logger.exception("Error durante la conciliación")
            st.error("Error durante la conciliación.")
            st.stop()

        # Resultados
        st.success("Conciliación completada.")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Coincidencias", len(coincidencias))
        m2.metric("Solo en A", len(solo_a))
        m3.metric("Solo en B", len(solo_b))
        m4.metric("Diferencias halladas", len(diferencias))

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

        # Descarga
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
        except Exception:
            logger.exception("Error al generar descarga")
            st.error("Error al generar el archivo de descarga.")

else:
    st.info("Por favor, sube ambos archivos para comenzar.")
