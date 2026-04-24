import logging
from io import BytesIO

import pandas as pd
import streamlit as st

from core.comparator import conciliar
from core.dtype_detector import detect_column_type, VALID_TYPES
from core.rules import apply_rule
from ui.column_mapper import column_mapper
from ui.rule_builder import rule_builder
from utils.file_loader import accepted_extensions, get_excel_sheets, load_dataframe

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="Conciliador de Planillas - IT Concesionaria", layout="wide")

st.title("Conciliador General de Planillas")
st.markdown("Compara dos archivos para encontrar coincidencias, faltantes y diferencias.")

TYPE_LABELS = {"str": "Texto", "int": "Número entero", "float": "Número decimal", "date": "Fecha"}


def _render_file_loader(label: str, col_key: str):
    """Renderiza el uploader + selector de hoja/decimal y retorna (df, decimal)."""
    file = st.file_uploader(label, type=accepted_extensions())
    if file is None:
        return None, "."

    decimal = "."
    if file.name.lower().endswith(".csv"):
        decimal = st.radio(
            "Separador decimal",
            [".", ","],
            horizontal=True,
            key=f"decimal_{col_key}",
            format_func=lambda x: f'Punto  "."  (ej: 1.50)' if x == "." else f'Coma  ","  (ej: 1,50)',
        )

    sheet = None
    if file.name.lower().endswith((".xlsx", ".xls", ".xlsm", ".xlsb")):
        sheets = get_excel_sheets(file.getvalue(), file.name)
        sheet = st.selectbox(f"Seleccionar hoja", sheets, key=f"sheet_{col_key}")
        if len(sheets) > 1:
            st.caption("📄 Este archivo tiene múltiples hojas")

    df = load_dataframe(file.getvalue(), file.name, sheet=sheet, decimal=decimal)
    return df, decimal


def _render_type_overrides(df, detected: dict, state_key: str, file_key: str):
    """Muestra grilla de selectboxes para corregir tipos de columnas."""
    if st.session_state.get(f"_file_key_{state_key}") != file_key:
        st.session_state[f"_file_key_{state_key}"] = file_key
        st.session_state[state_key] = dict(detected)

    overrides = st.session_state[state_key]
    col_list = list(df.columns)
    cols_per_row = 4

    for i in range(0, len(col_list), cols_per_row):
        row_cols = col_list[i:i + cols_per_row]
        ui_cols = st.columns(cols_per_row)
        for j, col_name in enumerate(row_cols):
            with ui_cols[j]:
                current = overrides.get(col_name, detected[col_name])
                new_type = st.selectbox(
                    f"**{col_name}**",
                    VALID_TYPES,
                    index=VALID_TYPES.index(current),
                    format_func=lambda t, col=col_name: (
                        f"{TYPE_LABELS[t]} ✏️" if t != detected.get(col) else TYPE_LABELS[t]
                    ),
                    key=f"{state_key}_{col_name}",
                    help=f"Detectado automáticamente: {TYPE_LABELS[detected[col_name]]}",
                )
                overrides[col_name] = new_type

    return overrides


# ── Carga de archivos ──────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Tabla A")
    df_a, decimal_a = _render_file_loader("Subir Tabla A (Ej: Administración)", "a")

with col2:
    st.markdown("#### Tabla B")
    df_b, decimal_b = _render_file_loader("Subir Tabla B (Ej: Movimientos)", "b")


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
        detected_a = {col: detect_column_type(df_a[col]) for col in df_a.columns}
        detected_b = {col: detect_column_type(df_b[col]) for col in df_b.columns}
    except Exception:
        logger.exception("Error al detectar tipos de columnas")
        st.error("Error al analizar las columnas del archivo.")
        st.stop()

    # ── Override manual de tipos ───────────────────────────────────────────────
    file_key = f"{df_a.shape}-{df_b.shape}-{list(df_a.columns)}-{list(df_b.columns)}"

    with st.expander("🔧 Corregir tipos de datos detectados (opcional)"):
        st.caption(
            "Si un tipo fue detectado incorrectamente (ej: código numérico tomado como fecha), "
            "podés corregirlo acá. El ✏️ indica columnas modificadas."
        )
        tab_a, tab_b = st.tabs(["Tabla A", "Tabla B"])
        with tab_a:
            col_types_a = _render_type_overrides(df_a, detected_a, "overrides_a", file_key)
        with tab_b:
            col_types_b = _render_type_overrides(df_b, detected_b, "overrides_b", file_key)

    col_types = col_types_a  # filtros se aplican sobre Tabla A

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

    # ── Mapeo de columnas ──────────────────────────────────────────────────────
    st.divider()
    key_mappings, compare_mappings = column_mapper(df_a, df_b, file_key)

    if st.button("Ejecutar Conciliación") and key_mappings:

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

        # Validar que las columnas mapeadas existen en cada tabla
        bad_a = [m["col_a"] for m in key_mappings + compare_mappings if m["col_a"] not in df_a.columns]
        bad_b = [m["col_b"] for m in key_mappings + compare_mappings if m["col_b"] not in df_b.columns]
        if bad_a:
            st.error(f"Columnas no encontradas en Tabla A: {', '.join(bad_a)}")
            st.stop()
        if bad_b:
            st.error(f"Columnas no encontradas en Tabla B: {', '.join(bad_b)}")
            st.stop()

        # Conciliar
        try:
            coincidencias, solo_a, solo_b, diferencias = conciliar(df_a, df_b, key_mappings, compare_mappings)
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
