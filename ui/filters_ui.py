import streamlit as st

def render_filter(col, dtype):
    st.write(f"### Filtro para {col} ({dtype})")
    
    if dtype in ["int", "float"]:
        rule = st.selectbox("Regla", [
            "equals", "not_equals", "greater", "less", "between"
        ], key=col)

    elif dtype == "str":
        rule = st.selectbox("Regla", [
            "contains", "not_contains", "starts_with", "ends_with"
        ], key=col)

    elif dtype == "date":
        rule = st.selectbox("Regla", [
            "before", "after", "between", "today"
        ], key=col)

    value = st.text_input("Valor", key=f"{col}_val")

    return rule, value