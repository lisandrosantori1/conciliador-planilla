"""Lógica de conciliación entre dos DataFrames."""

import pandas as pd


def conciliar(df_a, df_b, key_mappings, compare_mappings):
    """
    Realiza la conciliación entre dos DataFrames con mapeo flexible de columnas.

    Args:
        key_mappings:     Lista de {"col_a", "col_b", "fuzzy"} que identifican coincidencias.
        compare_mappings: Lista de {"col_a", "col_b"} donde detectar diferencias.

    Returns:
        Tuple (coincidencias, solo_a, solo_b, diferencias) como DataFrames.
    """
    key_cols_a = [m["col_a"] for m in key_mappings]
    has_fuzzy = any(m.get("fuzzy") for m in key_mappings)

    rename_b = {
        m["col_b"]: m["col_a"]
        for m in key_mappings + compare_mappings
        if m["col_a"] != m["col_b"]
    }
    df_b_aligned = df_b.rename(columns=rename_b)
    compare_cols = [m["col_a"] for m in compare_mappings]

    if has_fuzzy:
        fuzzy_cols = {m["col_a"] for m in key_mappings if m.get("fuzzy")}
        coincidencias, solo_a, solo_b = _fuzzy_merge(
            df_a, df_b_aligned, key_cols_a, fuzzy_cols, compare_cols
        )
    else:
        # Merge exacto con normalización de separador decimal
        df_a = df_a.copy()
        df_b_aligned = df_b_aligned.copy()
        for col in key_cols_a:
            df_a[col] = _normalize_key_col(df_a[col])
            df_b_aligned[col] = _normalize_key_col(df_b_aligned[col])

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


# ── Fuzzy merge ────────────────────────────────────────────────────────────────

def _fuzzy_key_match(val_a: str, val_b: str) -> bool:
    """Retorna True si uno de los valores contiene al otro (después de strip).

    Mínimo 3 caracteres para evitar falsos positivos con valores muy cortos.
    """
    a = str(val_a).strip()
    b = str(val_b).strip()
    if not a or not b or len(a) < 3 or len(b) < 3:
        return a == b
    return a in b or b in a


def _find_fuzzy_pairs(df_a, df_b, key_cols, fuzzy_cols):
    """Encuentra pares (idx_a, idx_b) que coinciden según las reglas de cada columna clave.

    Para columnas exactas normaliza el separador decimal.
    Para columnas fuzzy hace strip y verifica contenido.
    Cada fila de A se une con a lo sumo una fila de B (primera coincidencia).
    """
    # Pre-computar valores normalizados
    a_vals = {}
    b_vals = {}
    for col in key_cols:
        if col in fuzzy_cols:
            a_vals[col] = df_a[col].astype(str).str.strip().tolist()
            b_vals[col] = df_b[col].astype(str).str.strip().tolist()
        else:
            a_vals[col] = [_normalize_scalar(v) for v in df_a[col]]
            b_vals[col] = [_normalize_scalar(v) for v in df_b[col]]

    a_indices = list(df_a.index)
    b_indices = list(df_b.index)

    pairs = []
    used_b = set()

    for i, idx_a in enumerate(a_indices):
        for j, idx_b in enumerate(b_indices):
            if idx_b in used_b:
                continue
            match = True
            for col in key_cols:
                av = a_vals[col][i]
                bv = b_vals[col][j]
                if col in fuzzy_cols:
                    if not _fuzzy_key_match(av, bv):
                        match = False
                        break
                else:
                    if str(av) != str(bv):
                        match = False
                        break
            if match:
                pairs.append((idx_a, idx_b))
                used_b.add(idx_b)
                break

    return pairs


def _fuzzy_merge(df_a, df_b, key_cols, fuzzy_cols, compare_cols):
    """Construye coincidencias, solo_a y solo_b usando fuzzy matching."""
    pairs = _find_fuzzy_pairs(df_a, df_b, key_cols, fuzzy_cols)

    matched_a = [p[0] for p in pairs]
    matched_b = [p[1] for p in pairs]
    matched_a_set = set(matched_a)
    matched_b_set = set(matched_b)

    # Coincidencias: unir filas de A y B que matchearon
    if pairs:
        rows_a = df_a.loc[matched_a].reset_index(drop=True)
        rows_b = df_b.loc[matched_b].reset_index(drop=True)

        # Limpiar espacios en columnas fuzzy del resultado
        for col in fuzzy_cols:
            if col in rows_a.columns:
                rows_a[col] = rows_a[col].astype(str).str.strip()

        # Columnas de B que no son clave: agregarlas con sufijo _B si hay conflicto
        b_non_key = [c for c in df_b.columns if c not in key_cols]
        a_non_key = [c for c in df_a.columns if c not in key_cols]
        conflict = set(a_non_key) & set(b_non_key)

        rows_a_out = rows_a.rename(columns={c: f"{c}_A" for c in conflict})
        rows_b_out = rows_b[b_non_key].rename(columns={c: f"{c}_B" for c in conflict})

        coincidencias = pd.concat([rows_a_out, rows_b_out], axis=1)
        coincidencias["_merge"] = "both"
    else:
        coincidencias = pd.DataFrame()

    solo_a = df_a.loc[~df_a.index.isin(matched_a_set)].copy()
    solo_a["_merge"] = "left_only"

    solo_b = df_b.loc[~df_b.index.isin(matched_b_set)].copy()
    solo_b["_merge"] = "right_only"

    return coincidencias, solo_a, solo_b


# ── Normalización decimal ──────────────────────────────────────────────────────

def _normalize_scalar(val) -> str:
    """Versión escalar de normalización para uso en listas."""
    if pd.isna(val):
        return ''
    s = str(val).strip()
    f = _try_to_float(s)
    if f is None:
        return s
    return str(int(f)) if f == int(f) else f'{f:.10g}'


def _normalize_key_col(series: pd.Series) -> pd.Series:
    """Normaliza una columna clave unificando el separador decimal antes del merge."""
    return series.apply(_normalize_scalar)


def _try_to_float(val) -> float | None:
    """Parsea un valor como float tolerando coma o punto como separador decimal."""
    v = str(val).strip()
    if not v or v.lower() in ('nan', 'none', ''):
        return None

    has_comma = ',' in v
    has_dot = '.' in v

    try:
        if has_comma and has_dot:
            if v.rindex(',') > v.rindex('.'):
                v = v.replace('.', '').replace(',', '.')
            else:
                v = v.replace(',', '')
        elif has_comma:
            v = v.replace(',', '.')
        return float(v)
    except (ValueError, AttributeError):
        return None


# ── Detección de diferencias ───────────────────────────────────────────────────

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
        col_a_name = f"{col}_A"
        col_b_name = f"{col}_B"
        if col_a_name not in coincidencias.columns or col_b_name not in coincidencias.columns:
            continue
        a = coincidencias[col_a_name]
        b = coincidencias[col_b_name]
        both_null = a.isna() & b.isna()
        str_diff = pd.Series(
            [_values_differ(av, bv) for av, bv in zip(a.fillna(''), b.fillna(''))],
            index=a.index,
            dtype=bool
        )
        diff_flags[col] = ~both_null & str_diff

    if not diff_flags:
        return pd.DataFrame()

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
            **{col: row[col] for col in key_cols if col in row.index},
            "Columnas_con_diferencias": ", ".join(cols_with_diff),
            **{f"{col}_A": row[f"{col}_A"] for col in cols_with_diff},
            **{f"{col}_B": row[f"{col}_B"] for col in cols_with_diff},
        })

    return pd.DataFrame(records)
