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

    rename_b = {
        m["col_b"]: m["col_a"]
        for m in key_mappings + compare_mappings
        if m["col_a"] != m["col_b"]
    }
    df_b_aligned = df_b.rename(columns=rename_b)

    # Normalizar separador decimal en columnas clave para que "123,45" y "123.45" unan
    df_a = df_a.copy()
    df_b_aligned = df_b_aligned.copy()
    for col in key_cols_a:
        df_a[col] = _normalize_key_col(df_a[col])
        df_b_aligned[col] = _normalize_key_col(df_b_aligned[col])

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


def _normalize_key_col(series: pd.Series) -> pd.Series:
    """Normaliza una columna clave unificando el separador decimal antes del merge.

    Convierte "123,45" → "123.45" para que coincida con "123.45" del otro archivo.
    Los valores no numéricos (texto, códigos) se dejan sin cambios.
    """
    def normalize(val):
        if pd.isna(val):
            return val
        s = str(val).strip()
        f = _try_to_float(s)
        if f is None:
            return s
        # Formato canónico: sin decimal si es entero, punto como separador si no
        return str(int(f)) if f == int(f) else f'{f:.10g}'
    return series.apply(normalize)


def _try_to_float(val) -> float | None:
    """Parsea un valor como float tolerando coma o punto como separador decimal.

    Soporta:
      - "308743.8"   → 308743.8  (punto decimal estándar)
      - "308743,8"   → 308743.8  (coma decimal europeo)
      - "1.234,56"   → 1234.56   (europeo con miles)
      - "1,234.56"   → 1234.56   (anglosajón con miles)
    """
    v = str(val).strip()
    if not v or v.lower() in ('nan', 'none', ''):
        return None

    has_comma = ',' in v
    has_dot = '.' in v

    try:
        if has_comma and has_dot:
            # Determinar cuál es el separador decimal por su posición final
            if v.rindex(',') > v.rindex('.'):
                # Europeo: "1.234,56"
                v = v.replace('.', '').replace(',', '.')
            else:
                # Anglosajón: "1,234.56"
                v = v.replace(',', '')
        elif has_comma:
            # Solo coma → separador decimal: "308743,8"
            v = v.replace(',', '.')
        # Solo punto → ya está en formato estándar

        return float(v)
    except (ValueError, AttributeError):
        return None


def _values_differ(a_val, b_val) -> bool:
    """Compara dos valores considerando formatos decimales equivalentes."""
    a_str = str(a_val).strip()
    b_str = str(b_val).strip()

    if a_str == b_str:
        return False

    a_f = _try_to_float(a_str)
    b_f = _try_to_float(b_str)

    if a_f is not None and b_f is not None:
        return a_f != b_f

    return a_str != b_str


def _find_differences(coincidencias, compare_cols, key_cols):
    """Detecta filas con diferencias usando comparación vectorizada por columna."""
    if not compare_cols or coincidencias.empty:
        return pd.DataFrame()

    diff_flags = {}
    for col in compare_cols:
        a = coincidencias[f"{col}_A"]
        b = coincidencias[f"{col}_B"]
        both_null = a.isna() & b.isna()

        str_diff = pd.Series(
            [_values_differ(av, bv) for av, bv in zip(a.fillna(''), b.fillna(''))],
            index=a.index,
            dtype=bool
        )

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
