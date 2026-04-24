"""Componente de UI para mapear columnas entre Tabla A y Tabla B."""

import streamlit as st


def _default_key_mappings(df_a, df_b):
    """Pre-popula el mapeo con la primera columna en común, si existe."""
    common = [col for col in df_a.columns if col in df_b.columns]
    if common:
        return [{"col_a": common[0], "col_b": common[0]}]
    return [{"col_a": df_a.columns[0], "col_b": df_b.columns[0]}]


def _init_state(df_a, df_b, file_key: str):
    if st.session_state.get("_mapper_file_key") != file_key:
        st.session_state["_mapper_file_key"] = file_key
        st.session_state["key_mappings"] = _default_key_mappings(df_a, df_b)
        st.session_state["compare_mappings"] = []


def _mapping_row(df_a, df_b, mapping: dict, row_key: str, deletable: bool = True):
    """Renderiza una fila de mapeo col_a ↔ col_b con botón de borrar."""
    cols_a = list(df_a.columns)
    cols_b = list(df_b.columns)

    c1, arrow, c2, c3 = st.columns([5, 1, 5, 1])

    with c1:
        idx_a = cols_a.index(mapping["col_a"]) if mapping["col_a"] in cols_a else 0
        mapping["col_a"] = st.selectbox(
            "Tabla A", cols_a, index=idx_a, key=f"{row_key}_a", label_visibility="collapsed"
        )

    with arrow:
        st.markdown("<div style='text-align:center; margin-top:8px; font-size:20px'>↔</div>", unsafe_allow_html=True)

    with c2:
        idx_b = cols_b.index(mapping["col_b"]) if mapping["col_b"] in cols_b else 0
        mapping["col_b"] = st.selectbox(
            "Tabla B", cols_b, index=idx_b, key=f"{row_key}_b", label_visibility="collapsed"
        )

    with c3:
        st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)
        if deletable and st.button("❌", key=f"{row_key}_del"):
            return True  # señal de borrar

    return False


def column_mapper(df_a, df_b, file_key: str):
    """
    Renderiza la UI de mapeo de columnas entre Tabla A y Tabla B.

    Returns:
        Tuple (key_mappings, compare_mappings) — listas de {"col_a": ..., "col_b": ...}.
    """
    _init_state(df_a, df_b, file_key)

    # ── Columnas clave ──────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### 🔑 Columnas clave — identifican coincidencias")
        st.caption(
            "Elegí qué columna de **Tabla A** corresponde a qué columna de **Tabla B**. "
            "Pueden tener distinto nombre."
        )

        c_head1, _, c_head2, _ = st.columns([5, 1, 5, 1])
        with c_head1:
            st.markdown("**Tabla A**")
        with c_head2:
            st.markdown("**Tabla B**")

        to_delete = []
        for i, m in enumerate(st.session_state.key_mappings):
            should_delete = _mapping_row(df_a, df_b, m, f"km_{i}", deletable=True)
            if should_delete:
                to_delete.append(i)

        for i in reversed(to_delete):
            st.session_state.key_mappings.pop(i)
            st.rerun()

        if st.button("➕ Agregar columna clave", key="km_add"):
            st.session_state.key_mappings.append({
                "col_a": df_a.columns[0],
                "col_b": df_b.columns[0]
            })
            st.rerun()

    # ── Columnas a comparar ─────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### 📊 Columnas a comparar — detectan diferencias (opcional)")
        st.caption(
            "Si las columnas se llaman distinto en cada tabla, podés mapearlas aquí. "
            "Si no agregás ninguna, la conciliación solo muestra coincidencias y faltantes."
        )

        if st.session_state.compare_mappings:
            c_head1, _, c_head2, _ = st.columns([5, 1, 5, 1])
            with c_head1:
                st.markdown("**Tabla A**")
            with c_head2:
                st.markdown("**Tabla B**")

        to_delete = []
        for i, m in enumerate(st.session_state.compare_mappings):
            should_delete = _mapping_row(df_a, df_b, m, f"cm_{i}", deletable=True)
            if should_delete:
                to_delete.append(i)

        for i in reversed(to_delete):
            st.session_state.compare_mappings.pop(i)
            st.rerun()

        if st.button("➕ Agregar columna a comparar", key="cm_add"):
            st.session_state.compare_mappings.append({
                "col_a": df_a.columns[0],
                "col_b": df_b.columns[0]
            })
            st.rerun()

    return st.session_state.key_mappings, st.session_state.compare_mappings
