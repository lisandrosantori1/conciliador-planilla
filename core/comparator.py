"""Lógica de conciliación entre dos DataFrames."""

import pandas as pd


def conciliar(df_a, df_b, key_cols, compare_cols):
    """
    Realiza la conciliación entre dos DataFrames.

    Returns:
        Tuple (coincidencias, solo_a, solo_b, diferencias) como DataFrames.
    """
    df_merge = pd.merge(
        df_a, df_b,
        on=key_cols,
        how='outer',
        suffixes=('_A', '_B'),
        indicator=True
    )

    coincidencias = df_merge[df_merge['_merge'] == 'both'].copy()
    solo_a = df_merge[df_merge['_merge'] == 'left_only'].copy()
    solo_b = df_merge[df_merge['_merge'] == 'right_only'].copy()
    diferencias = _find_differences(coincidencias, compare_cols, key_cols)

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
