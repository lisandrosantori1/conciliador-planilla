"""Constructor visual de reglas de filtrado para Streamlit."""

import uuid
import datetime
import streamlit as st
import pandas as pd

from core.rule_labels import RULE_LABELS, RULE_LABELS_INV

HELP_TEXT = {
    "equals": "El valor debe ser exactamente igual",
    "greater": "Valores mayores al indicado",
    "less": "Valores menores al indicado",
    "between": "Valores dentro de un rango (desde-hasta)",
    "contains": "El texto debe contener este valor",
    "starts_with": "El texto debe comenzar con este valor",
    "ends_with": "El texto debe terminar con este valor",
    "before": "Fechas anteriores",
    "after": "Fechas posteriores"
}


def is_empty(value):
    """Retorna True si el valor es None, string vacío o NaN."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if pd.isna(value):
        return True
    return False


def _init_session_state(df):
    if "rules" not in st.session_state:
        st.session_state.rules = []
    if "logic" not in st.session_state:
        st.session_state.logic = "AND"
    if "new_rule" not in st.session_state:
        st.session_state.new_rule = {
            "col": df.columns[0],
            "condition": "equals",
            "value": "",
            "value2": ""
        }
    if "current_rule" not in st.session_state:
        st.session_state.current_rule = None


def _get_options_for_dtype(dtype):
    if dtype in ["int", "float"]:
        return ["equals", "greater", "less", "between"]
    elif dtype == "str":
        return ["contains", "starts_with", "ends_with", "equals"]
    else:
        return ["equals", "before", "after"]


def _render_value_input(rule, col_types, key_prefix):
    """Renderiza el widget de valor apropiado según el tipo y condición."""
    dtype = col_types[rule["col"]]
    condition = rule["condition"]

    if condition == "between":
        col3a, col3b = st.columns(2)
        with col3a:
            rule["value"] = st.text_input("Desde", key=f"{key_prefix}_val1")
        with col3b:
            rule["value2"] = st.text_input("Hasta", key=f"{key_prefix}_val2")

    elif dtype == "int":
        rule["value"] = st.number_input("Valor", step=1, key=f"{key_prefix}_val")

    elif dtype == "float":
        rule["value"] = st.number_input("Valor", key=f"{key_prefix}_val")

    elif dtype == "date":
        date_mode = st.selectbox(
            "Tipo de fecha",
            ["Manual", "Hoy", "Ayer", "Este mes", "Mes pasado"],
            key=f"{key_prefix}_date_mode"
        )
        today = datetime.date.today()

        if date_mode == "Hoy":
            rule["value"] = today
        elif date_mode == "Ayer":
            rule["value"] = today - datetime.timedelta(days=1)
        elif date_mode == "Este mes":
            rule["value"] = today.replace(day=1)
        elif date_mode == "Mes pasado":
            first_day = today.replace(day=1)
            last_month = first_day - datetime.timedelta(days=1)
            rule["value"] = last_month.replace(day=1)
        else:
            default_date = rule["value"] if isinstance(rule["value"], datetime.date) else None
            rule["value"] = st.date_input("Fecha", value=default_date, key=f"{key_prefix}_val")

    else:
        rule["value"] = st.text_input("Valor", key=f"{key_prefix}_val")


def rule_builder(df, col_types):
    """Renderiza el constructor de reglas y retorna (rules, logic)."""
    _init_session_state(df)

    st.subheader("🧠 Constructor de reglas")

    logic_map = {"Y": "AND", "O": "OR"}
    logic_label = st.segmented_control(
        "¿Cómo combinar las condiciones?",
        ["Y", "O"],
        selection_mode="single",
        default="Y" if st.session_state.logic == "AND" else "O",
        key="logic_selector_main"
    )
    st.session_state.logic = logic_map[logic_label]

    with st.container(border=True):
        st.markdown("### Nueva regla de filtro por columna")
        st.caption("Seleccioná una columna, la condición y el valor para filtrar registros.")
        if st.button("➕ Agregar regla"):
            st.session_state.current_rule = {
                "col": df.columns[0],
                "condition": "equals",
                "value": "",
                "value2": ""
            }

    rule = st.session_state.current_rule

    if rule:
        with st.container(border=True):
            st.info("✏️ Configurá la regla: elegí columna → condición → valor, luego **✅ Aplicar**.")

        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

        with col1:
            prev_col = rule["col"]
            rule["col"] = st.selectbox(
                "Columna", df.columns,
                index=list(df.columns).index(rule["col"]),
                key="current_col"
            )
            if rule["col"] != prev_col:
                rule["value"] = None
                rule["value2"] = None
                if "current_val" in st.session_state:
                    del st.session_state["current_val"]

        with col2:
            dtype = col_types[rule["col"]]
            options = _get_options_for_dtype(dtype)
            labels = [RULE_LABELS[o] for o in options]
            selected_label = st.selectbox("Requisito", labels, key="current_cond")
            rule["condition"] = RULE_LABELS_INV[selected_label]

        with col3:
            _render_value_input(rule, col_types, key_prefix="current")

        with col4:
            if st.button("❌ Cancelar", key="cancel_current"):
                st.session_state.current_rule = None
                st.rerun()

            if st.button("✅ Aplicar", key="apply_current"):
                if rule["condition"] == "between":
                    valid = not is_empty(rule["value"]) and not is_empty(rule["value2"])
                else:
                    valid = not is_empty(rule["value"])

                if valid:
                    st.session_state.rules.append({
                        "id": str(uuid.uuid4()),
                        **rule,
                        "status": "aplicada"
                    })
                    st.session_state.current_rule = None
                    st.rerun()
                else:
                    st.error("Completa la regla antes de aplicarla")

    with st.container(border=True):
        st.markdown("#### 📋 Reglas actuales")
        st.caption(
            "Reglas aplicadas sobre la tabla. Podés **editarlas** haciendo clic sobre la **columna**, "
            "**condición** o **valor**, o **eliminarlas** con el botón ❌. "
            "Hay ejemplo debajo del valor para cada tipo de dato."
        )
        st.write("")

        for i, r in enumerate(st.session_state.rules):
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

            with col1:
                prev_col = r["col"]
                r["col"] = st.selectbox(
                    "Columna", df.columns,
                    index=list(df.columns).index(r["col"]),
                    key=f"rule_{r['id']}_col"
                )

                if r["col"] != prev_col:
                    if "current_date_mode" in st.session_state:
                        del st.session_state["current_date_mode"]
                    dtype = col_types[r["col"]]
                    r["value"] = ""
                    r["value2"] = ""
                    r["status"] = "nueva"
                    r["condition"] = "equals" if dtype in ["int", "float", "date"] else "contains"
                    st.session_state.filters_applied = False

                r["status"] = "nueva"

            with col2:
                dtype = col_types[r["col"]]
                options = _get_options_for_dtype(dtype)
                labels = [RULE_LABELS[o] for o in options]
                selected_label = st.selectbox(
                    "Requisito", labels,
                    index=labels.index(RULE_LABELS[r["condition"]]) if r["condition"] in RULE_LABELS and RULE_LABELS[r["condition"]] in labels else 0,
                    key=f"rule_{r['id']}_cond"
                )
                r["condition"] = RULE_LABELS_INV[selected_label]
                st.session_state.filters_applied = False
                r["status"] = "nueva"

            with col3:
                dtype = col_types[r["col"]]
                condition = r["condition"]

                if condition == "between":
                    col3a, col3b = st.columns(2)
                    st.caption("Ej: desde 100 hasta 500")
                    with col3a:
                        val1 = st.text_input("Desde", value=r.get("value", ""), key=f"rule_{i}_val1")
                    with col3b:
                        val2 = st.text_input("Hasta", value=r.get("value2", ""), key=f"rule_{i}_val2")
                    r["value"] = val1
                    r["value2"] = val2
                    st.session_state.filters_applied = False
                    r["status"] = "nueva"

                elif dtype == "int":
                    r["value"] = st.number_input(
                        "Valor",
                        value=int(r["value"]) if str(r["value"]).isdigit() else 0,
                        step=1,
                        key=f"rule_{r['id']}_val"
                    )
                    st.caption("Ej: 100, 2500")

                elif dtype == "float":
                    r["value"] = st.number_input(
                        "Valor",
                        value=float(r["value"]) if r["value"] not in ["", None] else 0.0,
                        key=f"rule_{r['id']}_val"
                    )
                    st.caption("Ej: 100 o 99.5")

                elif dtype == "date":
                    default_date = r["value"] if isinstance(r["value"], datetime.date) else None
                    r["value"] = st.date_input("Fecha", value=default_date, key=f"rule_{r['id']}_val")
                    st.caption("Seleccionar desde el calendario")

                else:
                    r["value"] = st.text_input(
                        "Valor",
                        value=str(r["value"]) if r["value"] not in [None] else "",
                        key=f"rule_{r['id']}_val"
                    )
                    st.caption("Ej: Juan, ABC123, Cliente1")

            with col4:
                st.markdown("<div style='margin-top: 28px'></div>", unsafe_allow_html=True)
                if st.button("❌", key=f"rule_{r['id']}_del"):
                    st.session_state.rules.pop(i)
                    st.rerun()

    return st.session_state.rules, st.session_state.logic
