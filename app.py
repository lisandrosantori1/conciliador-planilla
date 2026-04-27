import logging
from io import BytesIO

import numpy as np
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
CALC_OPS = ["×", "+", "-", "÷"]

# ── Inicializar estado ─────────────────────────────────────────────────────────
if "n_tables" not in st.session_state:
    st.session_state.n_tables = 2


# ── Helpers ────────────────────────────────────────────────────────────────────

def _render_file_loader(label: str, col_key: str):
    file = st.file_uploader(label, type=accepted_extensions(), key=f"file_{col_key}")
    if file is None:
        return None, "."
    decimal = "."
    if file.name.lower().endswith(".csv"):
        decimal = st.radio(
            "Separador decimal", [".", ","], horizontal=True, key=f"decimal_{col_key}",
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
    if st.session_state.get(f"_fk_{state_key}") != file_key:
        st.session_state[f"_fk_{state_key}"] = file_key
        st.session_state[state_key] = dict(detected)
    overrides = st.session_state[state_key]
    for i in range(0, len(df.columns), 4):
        row_cols = list(df.columns)[i:i + 4]
        ui_cols = st.columns(4)
        for j, col_name in enumerate(row_cols):
            with ui_cols[j]:
                current = overrides.get(col_name, detected[col_name])
                new_type = st.selectbox(
                    f"**{col_name}**", VALID_TYPES, index=VALID_TYPES.index(current),
                    format_func=lambda t, c=col_name: (
                        f"{TYPE_LABELS[t]} ✏️" if t != detected.get(c) else TYPE_LABELS[t]
                    ),
                    key=f"{state_key}_{col_name}",
                    help=f"Detectado: {TYPE_LABELS[detected[col_name]]}",
                )
                overrides[col_name] = new_type
    return overrides


def _apply_filters(df, rules, logic, col_types):
    if not rules:
        return df
    mask = None
    for r in rules:
        m = apply_rule(
            df[r["col"]], r["condition"], r.get("value"), r.get("value2"),
            dtype=col_types.get(r["col"], "str"),
        )
        if m is None:
            continue
        mask = m if mask is None else (mask & m if logic == "AND" else mask | m)
    return df[mask] if mask is not None else df


def _apply_calc_cols(df: pd.DataFrame, defs: list) -> pd.DataFrame:
    """Agrega columnas calculadas al DataFrame según las definiciones."""
    if not defs:
        return df
    result = df.copy()
    for d in defs:
        c1, c2, op, name = d.get("col1"), d.get("col2"), d.get("op", "×"), d.get("name", "")
        if not name or c1 not in result.columns or c2 not in result.columns:
            continue
        try:
            a = pd.to_numeric(result[c1], errors="coerce")
            b = pd.to_numeric(result[c2], errors="coerce")
            if op == "×":
                result[name] = a * b
            elif op == "+":
                result[name] = a + b
            elif op == "-":
                result[name] = a - b
            elif op == "÷":
                result[name] = np.where(b != 0, a / b, np.nan)
        except Exception:
            logger.exception(f"Error calculando columna '{name}'")
    return result


def _numeric_cols_from(coinc: pd.DataFrame) -> list:
    """Columnas de coincidencias que son o pueden convertirse a número (int o float)."""
    cols = []
    for c in coinc.columns:
        if c == "_merge":
            continue
        if pd.api.types.is_numeric_dtype(coinc[c]):
            cols.append(c)
        else:
            # Columnas object que tienen al menos un valor numérico
            if pd.to_numeric(coinc[c], errors="coerce").notna().any():
                cols.append(c)
    return cols


def _render_calc_cols_section(coinc: pd.DataFrame):
    """UI para definir columnas calculadas sobre las coincidencias."""
    numeric_cols = _numeric_cols_from(coinc)

    with st.container(border=True):
        st.markdown("#### 🔢 Columnas calculadas — agregar a Coincidencias (opcional)")
        st.caption(
            "Definí operaciones entre columnas numéricas de cualquier tabla. "
            "Ejemplo: Cantidad × Precio unitario → Precio total."
        )

        if not numeric_cols:
            st.info("No hay columnas numéricas disponibles en Coincidencias.")
            return

        if "calc_definitions" not in st.session_state:
            st.session_state["calc_definitions"] = []

        defs = st.session_state["calc_definitions"]

        if defs:
            h1, h2, h3, h4, _ = st.columns([3, 1, 3, 3, 1])
            h1.caption("Columna 1 (cualquier tabla)")
            h2.caption("Op.")
            h3.caption("Columna 2 (cualquier tabla)")
            h4.caption("Nombre del resultado")

        to_delete = []
        for i, d in enumerate(defs):
            c1, c2, c3, c4, c5 = st.columns([3, 1, 3, 3, 1])
            with c1:
                d["col1"] = st.selectbox(
                    "", numeric_cols,
                    index=numeric_cols.index(d["col1"]) if d["col1"] in numeric_cols else 0,
                    key=f"cd_c1_{i}", label_visibility="collapsed",
                )
            with c2:
                d["op"] = st.selectbox(
                    "", CALC_OPS,
                    index=CALC_OPS.index(d.get("op", "×")),
                    key=f"cd_op_{i}", label_visibility="collapsed",
                )
            with c3:
                d["col2"] = st.selectbox(
                    "", numeric_cols,
                    index=numeric_cols.index(d["col2"]) if d["col2"] in numeric_cols else 0,
                    key=f"cd_c2_{i}", label_visibility="collapsed",
                )
            with c4:
                d["name"] = st.text_input(
                    "", value=d.get("name", f"Calculada_{i + 1}"),
                    key=f"cd_name_{i}", label_visibility="collapsed",
                    placeholder="Ej: Precio total",
                )
            with c5:
                st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)
                if st.button("❌", key=f"cd_del_{i}"):
                    to_delete.append(i)

            # Preview de la fórmula
            name_preview = d.get("name") or f"Calculada_{i + 1}"
            col1_preview = d.get("col1", "?")
            col2_preview = d.get("col2", "?")
            op_preview = d.get("op", "×")
            st.caption(f"→ **{name_preview}** = `{col1_preview}` **{op_preview}** `{col2_preview}`")

        for i in reversed(to_delete):
            defs.pop(i)
            st.session_state.pop("calc_applied", None)
            st.rerun()

        add_col, calc_col = st.columns([2, 2])
        with add_col:
            if st.button("➕ Agregar columna calculada", key="calc_add"):
                defs.append({
                    "col1": numeric_cols[0],
                    "op": "×",
                    "col2": numeric_cols[min(1, len(numeric_cols) - 1)],
                    "name": f"Calculada_{len(defs) + 1}",
                })
                st.session_state.pop("calc_applied", None)
                st.rerun()
        with calc_col:
            if defs and st.button("▶️ Calcular columnas", key="btn_calc", type="primary"):
                st.session_state["calc_applied"] = True
                st.rerun()


def _reset_filters_if_table_changed(table_key: str):
    if st.session_state.get("_active_table_key") != table_key:
        st.session_state["_active_table_key"] = table_key
        for k in ("rules", "current_rule", "key_mappings", "compare_mappings",
                  "concil_results", "calc_definitions", "calc_applied"):
            st.session_state.pop(k, None)
        st.session_state["logic"] = "AND"

#Comentado por el momento ya que no esta actualizado y molesta. Luego verlo
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
loaded_tables = []

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

with st.expander("🔧 Corregir tipos de datos detectados (opcional)"):
    st.caption("El ✏️ indica columnas modificadas manualmente.")
    type_tabs = st.tabs([t["label"] for t in loaded_tables])
    col_types_all = {}
    for tab_widget, table in zip(type_tabs, loaded_tables):
        with tab_widget:
            col_types_all[table["idx"]] = _render_type_overrides(
                table["df"], detected_all[table["idx"]],
                f"overrides_t{table['idx']}", global_file_key,
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
                "📥 Descargar resultado", output.getvalue(), "resultado_filtrado.xlsx",
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
                "Tabla B — destino / comparación", opts_b,
                index=opts_b.index(default_b), key="sel_b_val",
            )

    table_a = table_by_label[sel_a]
    table_b = table_by_label[sel_b]
    df_a = table_a["df"]
    df_b = table_b["df"]
    col_types = col_types_all[table_a["idx"]]

    active_key = f"recon-{table_a['idx']}-{table_b['idx']}-{global_file_key}"
    _reset_filters_if_table_changed(active_key)

    if df_a.empty or df_b.empty:
        st.error("Una de las tablas seleccionadas está vacía.")
        st.stop()

    _help_text()
    st.subheader("Filtros avanzados")
    st.write("")

    rules, logic = rule_builder(df_a, col_types)

    if not rules:
        st.info("ℹ️ Sin filtros. Se analizarán todos los registros de Tabla A.")
    else:
        st.success(f"🔍 Aplicando {len(rules)} filtro(s) con lógica '{logic}'")

    mapper_key = f"a{table_a['idx']}-b{table_b['idx']}-{df_a.shape}-{df_b.shape}-{list(df_a.columns)[:5]}"
    st.divider()
    key_mappings, compare_mappings = column_mapper(df_a, df_b, mapper_key)

    # Opciones de resultado
    with st.container(border=True):
        st.caption("Incluir en resultados y descarga:")
        oc1, oc2 = st.columns(2)
        with oc1:
            show_solo_a = st.checkbox(
                f"Registros solo en {sel_a}", value=False, key="show_solo_a",
                help=f"Filas de {sel_a} sin coincidencia en {sel_b}",
            )
        with oc2:
            show_solo_b = st.checkbox(
                f"Registros solo en {sel_b}", value=False, key="show_solo_b",
                help=f"Filas de {sel_b} sin coincidencia en {sel_a}",
            )

    if st.button("Ejecutar Conciliación", type="primary") and key_mappings:
        df_a_filtered = _apply_filters(df_a, rules, logic, col_types)

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

        # Guardar resultados para persistir entre reruns
        st.session_state["concil_results"] = {
            "coincidencias": coincidencias,
            "solo_a": solo_a,
            "solo_b": solo_b,
            "diferencias": diferencias,
            "df_a_filtered": df_a_filtered,
        }
        st.session_state.pop("calc_definitions", None)
        st.session_state.pop("calc_applied", None)

    # ── Mostrar resultados (persisten entre reruns) ────────────────────────────
    if "concil_results" in st.session_state:
        res = st.session_state["concil_results"]
        coincidencias = res["coincidencias"]
        solo_a = res["solo_a"]
        solo_b = res["solo_b"]
        diferencias = res["diferencias"]
        df_a_filtered = res["df_a_filtered"]

        # Métricas: solo mostrar solo_a/solo_b si el checkbox está activo
        st.success("Conciliación completada.")
        metric_cols = ["Coincidencias"]
        if show_solo_a:
            metric_cols.append(f"Solo en {sel_a}")
        if show_solo_b:
            metric_cols.append(f"Solo en {sel_b}")
        metric_cols.append("Diferencias halladas")

        m_cols = st.columns(len(metric_cols))
        mi = 0
        m_cols[mi].metric("Coincidencias", len(coincidencias)); mi += 1
        if show_solo_a:
            m_cols[mi].metric(f"Solo en {sel_a}", len(solo_a)); mi += 1
        if show_solo_b:
            m_cols[mi].metric(f"Solo en {sel_b}", len(solo_b)); mi += 1
        m_cols[mi].metric("Diferencias halladas", len(diferencias))

        # Columnas calculadas
        _render_calc_cols_section(coincidencias)

        # Aplicar cálculos solo cuando el usuario presionó "▶️ Calcular columnas"
        calc_defs = st.session_state.get("calc_definitions", [])
        if calc_defs and st.session_state.get("calc_applied"):
            coinc_con_calcs = _apply_calc_cols(coincidencias, calc_defs)
        else:
            coinc_con_calcs = coincidencias

        # Vista previa
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
                st.dataframe(coinc_con_calcs.head(10), use_container_width=True)
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

        # Descarga
        try:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_a_filtered.to_excel(writer, index=False, sheet_name=f"{sel_a} Original")
                df_b.to_excel(writer, index=False, sheet_name=f"{sel_b} Original")
                coinc_con_calcs.drop(columns=["_merge"], errors="ignore").to_excel(
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
