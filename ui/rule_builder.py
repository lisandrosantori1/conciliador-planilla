import streamlit as st
import datetime
import pandas as pd

from core.rule_labels import RULE_LABELS, RULE_LABELS_INV
HELP_TEXT = {
    "equals": "El valor debe ser exactamente igual",
    "greater": "Valores mayores al indicado",
    "less": "Valores menores al indicado",
    "between": "Valores dentro de un rango (desde-hasta)",
    "contains": "El texto debe contener este valor",
    "starts_with": "El texto debe comenzar con este valor",
    "before": "Fechas anteriores",
    "after": "Fechas posteriores"
}

def is_empty(value):
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if pd.isna(value):
        return True
    return False

def rule_builder(df, col_types):
    
    # Inicializar estado
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

    st.subheader("🧠 Constructor de reglas")

    # Estado
    if "rules" not in st.session_state:
        st.session_state.rules = []

    if "logic" not in st.session_state:
        st.session_state.logic = "AND"

    # Selector lógica global
    logic_map = {
        "Y": "AND",
        "O": "OR"
    }

    logic_label = st.segmented_control(
        "¿Cómo combinar las condiciones?",
        ["Y", "O"],
        selection_mode="single",
        default="Y" if st.session_state.logic == "AND" else "O",
        key="logic_selector_main"
    )

    st.session_state.logic = logic_map[logic_label]

    cols = df.columns.tolist()

    with st.container(border=True):
        st.markdown("### ➕ Nueva regla")

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

            st.warning("🆕 Regla en edición")

        col1, col2, col3, col4 = st.columns([2,2,2,1])

        # COLUMNA
        with col1:
            prev_col = rule["col"]

            rule["col"] = st.selectbox(
                "Columna",
                df.columns,
                index=list(df.columns).index(rule["col"]),
                key="current_col"
            )

            if rule["col"] != prev_col:
                rule["value"] = None
                rule["value2"] = None

                # 🔥 reset widgets
                if "current_val" in st.session_state:
                    del st.session_state["current_val"]

        # REQUISITO
        with col2:
            dtype = col_types[rule["col"]]

            if dtype in ["int", "float"]:
                options = ["equals", "greater", "less", "between"]
            elif dtype == "str":
                options = ["contains", "starts_with", "equals"]
            else:
                options = ["equals", "before", "after"]

            labels = [RULE_LABELS[o] for o in options]

            selected_label = st.selectbox(
                "Requisito",
                labels,
                key="current_cond"
            )

            rule["condition"] = RULE_LABELS_INV[selected_label]

        # VALOR
        with col3:
            dtype = col_types[rule["col"]]
            condition = rule["condition"]

            if condition == "between":
                col3a, col3b = st.columns(2)

                with col3a:
                    rule["value"] = st.text_input("Desde", key="current_val1")

                with col3b:
                    rule["value2"] = st.text_input("Hasta", key="current_val2")

            elif dtype == "int":
                rule["value"] = st.number_input("Valor", step=1, key="current_val")

            elif dtype == "float":
                rule["value"] = st.number_input("Valor", key="current_val")

            elif dtype == "date":

                # Selector modo fecha
                date_mode = st.selectbox(
                    "Tipo de fecha",
                    ["Manual", "Hoy", "Ayer", "Este mes", "Mes pasado"],
                    key="current_date_mode"
                )

                today = datetime.date.today()

                if date_mode == "Hoy":
                    rule["value"] = today

                elif date_mode == "Ayer":
                    rule["value"] = today - datetime.timedelta(days=1)

                elif date_mode == "Este mes":
                    rule["value"] = today.replace(day=1)

                elif date_mode == "Mes pasado":
                    first_day_this_month = today.replace(day=1)
                    last_month = first_day_this_month - datetime.timedelta(days=1)
                    rule["value"] = last_month.replace(day=1)

                else:
                    # Manual
                    default_date = None

                    if isinstance(rule["value"], datetime.date):
                        default_date = rule["value"]

                    rule["value"] = st.date_input(
                        "Fecha",
                        value=default_date,
                        key="current_val"
                    )
            
            else:
                rule["value"] = st.text_input("Valor", key="current_val")

        # BOTONES (columna derecha)
        with col4:
            if st.button("❌ Cancelar", key="cancel_current"):
                st.session_state.current_rule = None
                st.rerun()

            if st.button("✅ Aplicar", key="apply_current"):

                valid = False

                if rule["condition"] == "between":
                    valid = not is_empty(rule["value"]) and not is_empty(rule["value2"])
                else:
                    valid = not is_empty(rule["value"])

                if valid:
                    import uuid  # 👈 arriba del archivo

                    st.session_state.rules.append({
                        "id": str(uuid.uuid4()),  # 👈 clave única
                        **rule,
                        "status": "aplicada"
                    })
                    st.session_state.current_rule = None
                    st.rerun()
                else:
                    st.error("Completa la regla antes de aplicarla")

    with st.container(border=True):
        st.markdown("### 📋 Reglas actuales")

    for i, rule in enumerate(st.session_state.rules):

        col1, col2, col3, col4 = st.columns([2,2,2,1])

        # COLUMNA
        with col1:
            prev_col = rule["col"]

            rule["col"] = st.selectbox(
                f"Columna",
                df.columns,
                index=list(df.columns).index(rule["col"]),
                key=f"rule_{rule['id']}_col"
            )

            # 👉 SI CAMBIA LA COLUMNA → RESET VALORES
            if rule["col"] != prev_col:

                if "current_date_mode" in st.session_state:
                    del st.session_state["current_date_mode"]

                dtype = col_types[rule["col"]]

                # Reset valores
                rule["value"] = ""
                rule["value2"] = ""
                rule["status"] = "nueva"

                # Reset condición según tipo
                if dtype in ["int", "float"]:
                    rule["condition"] = "equals"
                elif dtype == "str":
                    rule["condition"] = "contains"
                else:
                    rule["condition"] = "equals"
                
                st.session_state.filters_applied = False
            
            rule["status"] = "nueva"

        # REQUISITO
        with col2:
            dtype = col_types[rule["col"]]

            if dtype in ["int", "float"]:
                options = ["equals", "greater", "less", "between"]
            elif dtype == "str":
                options = ["contains", "starts_with", "equals"]
            else:
                options = ["equals", "before", "after"]

            labels = [RULE_LABELS[o] for o in options]

            selected_label = st.selectbox(
                f"Requisito",
                labels,
                index=labels.index(RULE_LABELS[rule["condition"]]),
                key=f"rule_{rule['id']}_cond"
            )

            rule["condition"] = RULE_LABELS_INV[selected_label]

            st.session_state.filters_applied = False
            rule["status"] = "nueva"

        # VALOR
        with col3:
            dtype = col_types[rule["col"]]
            condition = rule["condition"]

            # BETWEEN → 2 valores
            if condition == "between":
                col3a, col3b = st.columns(2)
                st.caption("Ej: desde 100 hasta 500")

                with col3a:
                    val1 = st.text_input(
                        f"Desde",
                        value=rule.get("value", ""),
                        key=f"rule_{i}_val1"
                    )

                with col3b:
                    val2 = st.text_input(
                        f"Hasta",
                        value=rule.get("value2", ""),
                        key=f"rule_{i}_val2"
                    )

                rule["value"] = val1

                st.session_state.filters_applied = False
                rule["status"] = "nueva"

                rule["value2"] = val2

            # NUMÉRICOS
            elif dtype == "int":
                rule["value"] = st.number_input(
                    f"Valor",
                    value=int(rule["value"]) if str(rule["value"]).isdigit() else 0,
                    step=1,
                    key=f"rule_{rule['id']}_val"
                )
                st.caption("Ej: 100, 2500")

            elif dtype == "float":
                rule["value"] = st.number_input(
                    f"Valor",
                    value=float(rule["value"]) if rule["value"] not in ["", None] else 0.0,
                    key=f"rule_{rule['id']}_val"
                )
                st.caption("Ej: 100 o 99.5")

            # FECHAS
            elif dtype == "date":

                # 👉 convertir valor previo si existe
                default_date = None
                if isinstance(rule["value"], datetime.date):
                    default_date = rule["value"]

                rule["value"] = st.date_input(
                    "Fecha",
                    value=default_date,
                    key=f"rule_{rule['id']}_val"
                )
                st.caption("Seleccionar desde el calendario")

            # TEXTO
            else:
                rule["value"] = st.text_input(
                    f"Valor",
                    value=str(rule["value"]) if rule["value"] not in [None] else "",
                    key=f"rule_{rule['id']}_val"
                )
                st.caption("Ej: Juan, ABC123, Cliente1")

        # ELIMINAR
        with col4:
            st.markdown(
                "<div style='margin-top: 28px'></div>", 
                unsafe_allow_html=True
            )  # 👈 baja el botón

            if st.button("❌", key=f"rule_{rule['id']}_del"):
                st.session_state.rules.pop(i)
                st.rerun()

    return st.session_state.rules, st.session_state.logic