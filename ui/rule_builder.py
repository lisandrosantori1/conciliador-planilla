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


def _init_session_state(df, p=""):
    if f"{p}rules" not in st.session_state:
        st.session_state[f"{p}rules"] = []
    if f"{p}logic" not in st.session_state:
        st.session_state[f"{p}logic"] = "AND"
    if f"{p}new_rule" not in st.session_state:
        st.session_state[f"{p}new_rule"] = {
            "col": df.columns[0],
            "condition": "equals",
            "value": "",
            "value2": ""
        }
    if f"{p}current_rule" not in st.session_state:
        st.session_state[f"{p}current_rule"] = None


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


def rule_builder(df, col_types, state_prefix=""):
    """
    Renderiza el constructor de reglas y retorna (rules, logic).

    state_prefix: prefijo para aislar el estado cuando se llama múltiples veces
    en la misma página (ej: "m2a_" para Tabla A, "m2b_" para Tabla B).
    """
    p = state_prefix
    _init_session_state(df, p)

    logic_map = {"Y": "AND", "O": "OR"}
    logic_label = st.segmented_control(
        "¿Cómo combinar las condiciones?",
        ["Y", "O"],
        selection_mode="single",
        default="Y" if st.session_state[f"{p}logic"] == "AND" else "O",
        key=f"{p}logic_selector_main"
    )
    st.session_state[f"{p}logic"] = logic_map[logic_label]

    with st.container(border=True):
        st.markdown("### Nueva regla de filtro por columna")
        st.caption("Seleccioná una columna, la condición y el valor para filtrar registros.")
        if st.button("➕ Agregar regla", key=f"{p}btn_add_rule"):
            st.session_state[f"{p}current_rule"] = {
                "col": df.columns[0],
                "condition": "equals",
                "value": "",
                "value2": ""
            }

    rule = st.session_state[f"{p}current_rule"]

    if rule:
        with st.container(border=True):
            st.info("✏️ Configurá la regla: elegí columna → condición → valor, luego **✅ Aplicar**.")

        col1, col2, col3, col_ok, col_x = st.columns([2, 2, 2, 1, 1])

        with col1:
            prev_col = rule["col"]
            rule["col"] = st.selectbox(
                "Columna", df.columns,
                index=list(df.columns).index(rule["col"]),
                key=f"{p}current_col"
            )
            if rule["col"] != prev_col:
                rule["value"] = None
                rule["value2"] = None
                if f"{p}current_val" in st.session_state:
                    del st.session_state[f"{p}current_val"]

        with col2:
            dtype = col_types[rule["col"]]
            options = _get_options_for_dtype(dtype)
            labels = [RULE_LABELS[o] for o in options]
            selected_label = st.selectbox("Requisito", labels, key=f"{p}current_cond")
            rule["condition"] = RULE_LABELS_INV[selected_label]

        with col3:
            _render_value_input(rule, col_types, key_prefix=f"{p}current")

        with col_ok:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            apply_clicked = st.button("✅", key=f"{p}apply_current")

        with col_x:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            cancel_clicked = st.button("❌", key=f"{p}cancel_current")

        if cancel_clicked:
            st.session_state[f"{p}current_rule"] = None
            st.rerun()
        if apply_clicked:
            if rule["condition"] == "between":
                valid = not is_empty(rule["value"]) and not is_empty(rule["value2"])
            else:
                valid = not is_empty(rule["value"])
            if valid:
                st.session_state[f"{p}rules"].append({
                    "id": str(uuid.uuid4()),
                    **rule,
                    "status": "aplicada"
                })
                st.session_state[f"{p}current_rule"] = None
                st.rerun()
            else:
                st.error("Completa la regla antes de aplicarla")

    if st.session_state[f"{p}rules"]:
        with st.container(border=True):
            st.markdown("#### 📋 Reglas actuales")
            st.caption(
                "Podés **editarlas** haciendo clic en la **columna**, **condición** o **valor**. "
                "Usá ❌ para eliminar una regla. "
                "Debajo de cada campo de valor hay un ejemplo del formato esperado."
            )

            for i, r in enumerate(st.session_state[f"{p}rules"]):
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

                with col1:
                    prev_col = r["col"]
                    r["col"] = st.selectbox(
                        "Columna", df.columns,
                        index=list(df.columns).index(r["col"]),
                        key=f"{p}rule_{r['id']}_col"
                    )

                    if r["col"] != prev_col:
                        if f"{p}current_date_mode" in st.session_state:
                            del st.session_state[f"{p}current_date_mode"]
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
                        key=f"{p}rule_{r['id']}_cond"
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
                            val1 = st.text_input("Desde", value=r.get("value", ""), key=f"{p}rule_{i}_val1")
                        with col3b:
                            val2 = st.text_input("Hasta", value=r.get("value2", ""), key=f"{p}rule_{i}_val2")
                        r["value"] = val1
                        r["value2"] = val2
                        st.session_state.filters_applied = False
                        r["status"] = "nueva"

                    elif dtype == "int":
                        r["value"] = st.number_input(
                            "Valor",
                            value=int(r["value"]) if str(r["value"]).isdigit() else 0,
                            step=1,
                            key=f"{p}rule_{r['id']}_val"
                        )
                        st.caption("Ej: 100, 2500")

                    elif dtype == "float":
                        r["value"] = st.number_input(
                            "Valor",
                            value=float(r["value"]) if r["value"] not in ["", None] else 0.0,
                            key=f"{p}rule_{r['id']}_val"
                        )
                        st.caption("Ej: 100 o 99.5")

                    elif dtype == "date":
                        default_date = r["value"] if isinstance(r["value"], datetime.date) else None
                        r["value"] = st.date_input("Fecha", value=default_date, key=f"{p}rule_{r['id']}_val")
                        st.caption("Seleccionar desde el calendario")

                    else:
                        r["value"] = st.text_input(
                            "Valor",
                            value=str(r["value"]) if r["value"] not in [None] else "",
                            key=f"{p}rule_{r['id']}_val"
                        )
                        st.caption("Ej: Juan, ABC123, Cliente1")

                with col4:
                    st.markdown("<div style='margin-top: 28px'></div>", unsafe_allow_html=True)
                    if st.button("❌", key=f"{p}rule_{r['id']}_del"):
                        st.session_state[f"{p}rules"].pop(i)
                        st.rerun()

                # ── Transformaciones (indentadas, opcionales) ──────────────────
                _, transform_area = st.columns([1, 11])
                with transform_area:
                    r.setdefault("transforms", [])
                    r["show_transforms"] = st.checkbox(
                        "Modificar una o más columnas para estas filas",
                        value=r.get("show_transforms", False),
                        key=f"{p}rule_{r['id']}_show_tr",
                        help="Aplicá una operación numérica a una columna en las filas que cumplan esta regla.",
                    )
                    if r["show_transforms"]:
                        TRANSFORM_OPS = ["×-1", "×", "+", "-", "÷"]
                        to_del_tr = []
                        for ti, t in enumerate(r["transforms"]):
                            tc1, tc2, tc3, tc4 = st.columns([3, 2, 3, 1])
                            with tc1:
                                t["col"] = st.selectbox(
                                    "Col", list(df.columns),
                                    index=list(df.columns).index(t["col"]) if t.get("col") in df.columns else 0,
                                    key=f"{p}tr_{r['id']}_{ti}_col", label_visibility="collapsed",
                                )
                            with tc2:
                                t["op"] = st.selectbox(
                                    "Op", TRANSFORM_OPS,
                                    index=TRANSFORM_OPS.index(t.get("op", "×-1")),
                                    key=f"{p}tr_{r['id']}_{ti}_op", label_visibility="collapsed",
                                )
                            with tc3:
                                if t.get("op", "×-1") != "×-1":
                                    t["val"] = st.number_input(
                                        "Val", value=float(t.get("val") or 1.0),
                                        key=f"{p}tr_{r['id']}_{ti}_val", label_visibility="collapsed",
                                    )
                                else:
                                    st.caption("Cambia el signo (×−1)")
                            with tc4:
                                if st.button("❌", key=f"{p}tr_{r['id']}_{ti}_del"):
                                    to_del_tr.append(ti)
                        for ti in reversed(to_del_tr):
                            r["transforms"].pop(ti)
                            st.rerun()
                        if st.button("➕ Agregar transformación", key=f"{p}tr_{r['id']}_add"):
                            r["transforms"].append({"col": list(df.columns)[0], "op": "×-1", "val": None})
                            st.rerun()

    return st.session_state[f"{p}rules"], st.session_state[f"{p}logic"]
