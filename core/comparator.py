"""Lógica de conciliación entre dos DataFrames."""

import pandas as pd


def conciliar(df_a, df_b, key_mappings, compare_mappings):
    """
    Realiza la conciliación entre dos DataFrames con mapeo flexible de columnas.

    Args:
        key_mappings:     Lista de {"col_a": ..., "col_b": ...} que identifican coincidencias.
        compare_mappings: Lista de {"col_a": ..., "col_b": ...} donde detectar diferencias.

    Returns:
        Tuple (coincidencias, solo_a, solo_b, diferencias) como DataFrames.
    """
    key_cols_a = [m["col_a"] for m in key_mappings]

    # Renombrar columnas de df_b al nombre equivalente en df_a para poder hacer el merge
    rename_b = {
        m["col_b"]: m["col_a"]
        for m in key_mappings + compare_mappings
        if m["col_a"] != m["col_b"]
    }
    df_b_aligned = df_b.rename(columns=rename_b)

    compare_cols = [m["col_a"] for m in compare_mappings]

    df_merge = pd.merge(
        df_a, df_b_aligned,
        on=key_cols_a,
        how='outer',
        suffixes=('_A', '_B'),
        indicator=True
    )

    coincidencias = df_merge[df_merge['_merge'] == 'both'].copy()
    solo_a = df_merge[df_merge['_merge'] == 'left_only'].copy()
    solo_b = df_merge[df_merge['_merge'] == 'right_only'].copy()
    diferencias = _find_differences(coincidencias, compare_cols, key_cols_a)

    return coincidencias, solo_a, solo_b, diferencias


def _find_differences(coincidencias, compare_cols, key_cols):
    """Detecta filas con diferencias usando comparación vectorizada por columna."""
    if not compare_cols or coincidencias.empty:
        return pd.DataFrame()

    diff_flags = {}
    for col in compare_cols:
        a = coincidencias[f"{col}_A"]
        b = coincidencias[f"{col}_B"]
        both_null = a.isna() & b.isna()
        str_diff = a.astype(str).str.strip() != b.astype(str).str.strip()
        diff_flags[col] = ~both_null & str_diff

    diff_df = pd.DataFrame(diff_flags, index=coincidencias.index)
    has_diff = diff_df.any(axis=1)

    if not has_diff.any():
        return pd.DataFrame()

    rows = coincidencias[has_diff]
    diff_mask = diff_df[has_diff]

    records = []
    for idx, row in rows.iterrows():
        cols_with_diff = diff_mask.columns[diff_mask.loc[idx]].tolist()
        records.append({
            **{col: row[col] for col in key_cols},
            "Columnas_con_diferencias": ", ".join(cols_with_diff),
            **{f"{col}_A": row[f"{col}_A"] for col in cols_with_diff},
            **{f"{col}_B": row[f"{col}_B"] for col in cols_with_diff},
        })

    return pd.DataFrame(records)
