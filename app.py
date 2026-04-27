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
st.markdown("Cargá entre 1 y 4 planillas para filtrar datos o buscar coincidencias.")

TYPE_LABELS = {"str": "Texto", "int": "Número entero", "float": "Número decimal", "date": "Fecha"}

# ── Inicializar estado ─────────────────────────────────────────────────────────
if "n_tables" not in st.session_state:
    st.session_state.n_tables = 2


# ── Helpers ───────────────────────────────────────────────────────────────────

def _render_file_loader(label: str, col_key: str):
    """Uploader con selector de hoja y separador decimal. Retorna (df, decimal)."""
    file = st.file_uploader(label, type=accepted_extensions(), key=f"file_{col_key}")
    if file is None:
        return None, "."

    decimal = "."
    if file.name.lower().endswith(".csv"):
        decimal = st.radio(
            "Separador decimal",
            [".", ","],
            horizontal=True,
            key=f"decimal_{col_key}",
            format_func=lambda x: f'Punto "." (ej: 1.50)' if x == "." else f'Coma "," (ej: 1,50)',
        )

    sheet = None
    if file.name.lower().endswith((".xlsx", ".xls", ".xlsm", ".xlsb")):
        sheets = get_excel_sheets(file.getvalue(), file.name)
        sheet = st.selectbox("Seleccionar hoja", sheets, key=f"sheet_{col_key}")
        if len(sheets) > 1:
            st.caption("📄 Este archivo tiene múltiples hojas")

    df = load_dataframe(file.getvalue(), file.name, sheet=sheet, decimal=decimal)
    return df, decimal


def _render_type_overrides(df, detected: dict, state_key: str, file_key: str):
    """Grilla de selectboxes para corregir tipos de columnas detectados."""
    if st.session_state.get(f"_fk_{state_key}") != file_key:
        st.session_state[f"_fk_{state_key}"] = file_key
        st.session_state[state_key] = dict(detected)

    overrides = st.session_state[state_key]
    cols_per_row = 4

    for i in range(0, len(df.columns), cols_per_row):
        row_cols = list(df.columns)[i:i + cols_per_row]
        ui_cols = st.columns(cols_per_row)
        for j, col_name in enumerate(row_cols):
            with ui_cols[j]:
                current = overrides.get(col_name, detected[col_name])
                new_type = st.selectbox(
                    f"**{col_name}**",
                    VALID_TYPES,
                    index=VALID_TYPES.index(current),
                    format_func=lambda t, c=col_name: (
                        f"{TYPE_LABELS[t]} ✏️" if t != detected.get(c) else TYPE_LABELS[t]
                    ),
                    key=f"{state_key}_{col_name}",
                    help=f"Detectado: {TYPE_LABELS[detected[col_name]]}",
                )
                overrides[col_name] = new_type
    return overrides


def _apply_filters(df, rules, logic, col_types):
    """Aplica reglas de filtrado sobre un DataFrame."""
    if not rules:
        return df
    mask = None
    for r in rules:
        m = apply_rule(
            df[r["col"]], r["condition"],
            r.get("value"), r.get("value2"),
            dtype=col_types.get(r["col"], "str")
        )
        if m is None:
            continue
        mask = m if mask is None else (mask & m if logic == "AND" else mask | m)
    return df[mask] if mask is not None else df


def _reset_filters_if_table_changed(table_key: str):
    """Limpia reglas y mapeo cuando el usuario cambia la tabla seleccionada."""
    if st.session_state.get("_active_table_key") != table_key:
        st.session_state["_active_table_key"] = table_key
        for k in ("rules", "current_rule", "key_mappings", "compare_mappings"):
            st.session_state.pop(k, None)
        st.session_state["logic"] = "AND"


def _help_text():
    with st.expander("ℹ️ ¿Cómo usar los filtros?"):
        st.markdown("""
**Paso a paso:**
1. Elegí una columna (Nombre, Fecha, ID…)
2. Elegí una condición (contiene, mayor que, entre…)
3. Ingresá el valor y hacé clic en **➕ Agregar regla**

**Combinar condiciones:**
- **Y** → se cumplen TODAS las condiciones
- **O** → se cumple AL MENOS una
        """)


# ── Carga de archivos ──────────────────────────────────────────────────────────
n = st.session_state.n_tables
loaded_tables = []  # lista de {"idx", "label", "df"}

for row_start in range(0, n, 2):
    slots = min(2, n - row_start)
    row = st.columns(slots)
    for j in range(slots):
        idx = row_start + j
        with row[j]:
            st.markdown(f"#### Tabla {idx + 1}")
            df, _ = _render_file_loader(f"Subir Tabla {idx + 1}", f"t{idx}")
            if df is not None and not df.empty:
                loaded_tables.append({"idx": idx, "label": f"Tabla {idx + 1}", "df": df})

# Botones agregar / quitar tabla
btn1, btn2, _ = st.columns([1, 1, 8])
with btn1:
    if n < 4 and st.button("➕ Tabla", help="Agregar una tabla más (máx. 4)"):
        st.session_state.n_tables += 1
        st.rerun()
with btn2:
    if n > 1 and st.button("➖ Tabla", help="Reducir cantidad de cargadores"):
        st.session_state.n_tables -= 1
        st.rerun()

if not loaded_tables:
    st.info("Cargá al menos un archivo para comenzar.")
    st.stop()

# ── Detección de tipos ─────────────────────────────────────────────────────────
try:
    detected_all = {
        t["idx"]: {col: detect_column_type(t["df"][col]) for col in t["df"].columns}
        for t in loaded_tables
    }
except Exception:
    logger.exception("Error al detectar tipos")
    st.error("Error al analizar columnas del archivo.")
    st.stop()

global_file_key = "_".join(
    f"{t['idx']}-{t['df'].shape[0]}x{len(t['df'].columns)}"
    for t in loaded_tables
)

# ── Override de tipos ──────────────────────────────────────────────────────────
with st.expander("🔧 Corregir tipos de datos detectados (opcional)"):
    st.caption("El ✏️ indica columnas modificadas manualmente.")
    type_tabs = st.tabs([t["label"] for t in loaded_tables])
    col_types_all = {}
    for tab_widget, table in zip(type_tabs, loaded_tables):
        with tab_widget:
            col_types_all[table["idx"]] = _render_type_overrides(
                table["df"],
                detected_all[table["idx"]],
                f"overrides_t{table['idx']}",
                global_file_key,
            )

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# MODO 1: Una sola tabla — filtrado
# ══════════════════════════════════════════════════════════════════════════════
if len(loaded_tables) == 1:
    table = loaded_tables[0]
    df = table["df"]
    col_types = col_types_all[table["idx"]]

    _reset_filters_if_table_changed(f"single-t{table['idx']}-{global_file_key}")

    st.subheader("🔍 Modo filtro — una sola planilla")
    st.caption("Aplicá filtros para encontrar y descargar registros específicos.")

    _help_text()

    rules, logic = rule_builder(df, col_types)

    if not rules:
        st.info("Sin filtros activos. Se mostrarán todos los registros al aplicar.")
    else:
        st.success(f"🔍 {len(rules)} filtro(s) activo(s) con lógica '{logic}'")

    if st.button("Aplicar filtros", type="primary"):
        resultado = _apply_filters(df, rules, logic, col_types)
        st.success(f"Mostrando {len(resultado):,} de {len(df):,} registros")
        st.dataframe(resultado, use_container_width=True)

        try:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                resultado.to_excel(writer, index=False, sheet_name="Resultados")
            st.download_button(
                "📥 Descargar resultado",
                output.getvalue(),
                "resultado_filtrado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            logger.exception("Error al generar descarga")
            st.error("Error al generar el archivo de descarga.")

# ══════════════════════════════════════════════════════════════════════════════
# MODO 2: Dos o más tablas — conciliación
# ══════════════════════════════════════════════════════════════════════════════
else:
    labels = [t["label"] for t in loaded_tables]
    table_by_label = {t["label"]: t for t in loaded_tables}

    # Selector de tablas A y B
    with st.container(border=True):
        st.markdown("#### Seleccionar tablas a conciliar")
        c1, c2 = st.columns(2)
        with c1:
            sel_a = st.selectbox("Tabla A — origen / referencia", labels, key="sel_a")
        with c2:
            opts_b = [l for l in labels if l != sel_a]
            cur_b = st.session_state.get("sel_b_val")
            default_b = cur_b if cur_b in opts_b else opts_b[0]
            sel_b = st.selectbox(
                "Tabla B — destino / comparación",
                opts_b,
                index=opts_b.index(default_b),
                key="sel_b_val",
            )

    table_a = table_by_label[sel_a]
    table_b = table_by_label[sel_b]
    df_a = table_a["df"]
    df_b = table_b["df"]
    col_types = col_types_all[table_a["idx"]]

    # Reset de reglas y mapeo si cambia la selección de tablas
    active_key = f"recon-{table_a['idx']}-{table_b['idx']}-{global_file_key}"
    _reset_filters_if_table_changed(active_key)

    if df_a.empty or df_b.empty:
        st.error("Una de las tablas seleccionadas está vacía.")
        st.stop()

    # Filtros sobre Tabla A
    _help_text()
    st.subheader("Filtros avanzados")
    rules, logic = rule_builder(df_a, col_types)

    if not rules:
        st.info("ℹ️ Sin filtros. Se analizarán todos los registros de Tabla A.")
    else:
        st.success(f"🔍 Aplicando {len(rules)} filtro(s) con lógica '{logic}'")

    # Mapeo de columnas
    mapper_key = f"a{table_a['idx']}-b{table_b['idx']}-{df_a.shape}-{df_b.shape}-{list(df_a.columns)[:5]}"
    st.divider()
    key_mappings, compare_mappings = column_mapper(df_a, df_b, mapper_key)

    # Opciones de resultado (antes del botón)
    with st.container(border=True):
        st.caption("Incluir en resultados y descarga:")
        oc1, oc2 = st.columns(2)
        with oc1:
            show_solo_a = st.checkbox(
                f"Registros solo en {sel_a}",
                value=False,
                key="show_solo_a",
                help=f"Filas que existen en {sel_a} pero no tienen coincidencia en {sel_b}",
            )
        with oc2:
            show_solo_b = st.checkbox(
                f"Registros solo en {sel_b}",
                value=False,
                key="show_solo_b",
                help=f"Filas que existen en {sel_b} pero no tienen coincidencia en {sel_a}",
            )

    if st.button("Ejecutar Conciliación", type="primary") and key_mappings:

        # Aplicar filtros a df_a
        df_a_filtered = _apply_filters(df_a, rules, logic, col_types)

        # Validar columnas mapeadas
        bad_a = [m["col_a"] for m in key_mappings + compare_mappings if m["col_a"] not in df_a_filtered.columns]
        bad_b = [m["col_b"] for m in key_mappings + compare_mappings if m["col_b"] not in df_b.columns]
        if bad_a:
            st.error(f"Columnas no encontradas en {sel_a}: {', '.join(bad_a)}")
            st.stop()
        if bad_b:
            st.error(f"Columnas no encontradas en {sel_b}: {', '.join(bad_b)}")
            st.stop()

        try:
            coincidencias, solo_a, solo_b, diferencias = conciliar(
                df_a_filtered, df_b, key_mappings, compare_mappings
            )
        except Exception:
            logger.exception("Error durante la conciliación")
            st.error("Error durante la conciliación.")
            st.stop()

        # Métricas (siempre se muestran los conteos)
        st.success("Conciliación completada.")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Coincidencias", len(coincidencias))
        m2.metric(f"Solo en {sel_a}", len(solo_a))
        m3.metric(f"Solo en {sel_b}", len(solo_b))
        m4.metric("Diferencias halladas", len(diferencias))

        # Armar tabs según opciones seleccionadas
        tab_names = ["Coincidencias"]
        if show_solo_a:
            tab_names.append(f"Solo en {sel_a}")
        if show_solo_b:
            tab_names.append(f"Solo en {sel_b}")
        tab_names.append("Diferencias")

        with st.expander("Vista previa de resultados", expanded=True):
            result_tabs = st.tabs(tab_names)
            ti = 0
            with result_tabs[ti]:
                st.dataframe(coincidencias.head(10), use_container_width=True)
            ti += 1
            if show_solo_a:
                with result_tabs[ti]:
                    st.dataframe(solo_a.head(10), use_container_width=True)
                ti += 1
            if show_solo_b:
                with result_tabs[ti]:
                    st.dataframe(solo_b.head(10), use_container_width=True)
                ti += 1
            with result_tabs[ti]:
                if not diferencias.empty:
                    st.dataframe(diferencias.head(10), use_container_width=True)
                else:
                    st.info("No se encontraron diferencias en las columnas seleccionadas.")

        try:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_a_filtered.to_excel(writer, index=False, sheet_name=f"{sel_a} Original")
                df_b.to_excel(writer, index=False, sheet_name=f"{sel_b} Original")
                coincidencias.drop(columns=["_merge"], errors="ignore").to_excel(
                    writer, index=False, sheet_name="Coincidencias"
                )
                if show_solo_a:
                    solo_a.drop(columns=["_merge"], errors="ignore").to_excel(
                        writer, index=False, sheet_name=f"Solo en {sel_a}"[:31]
                    )
                if show_solo_b:
                    solo_b.drop(columns=["_merge"], errors="ignore").to_excel(
                        writer, index=False, sheet_name=f"Solo en {sel_b}"[:31]
                    )
                if not diferencias.empty:
                    diferencias.to_excel(writer, index=False, sheet_name="Diferencias")

            st.download_button(
                "📥 Descargar Reporte de Conciliación",
                output.getvalue(),
                "conciliacion_resultado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            logger.exception("Error al generar descarga")
            st.error("Error al generar el archivo de descarga.")
