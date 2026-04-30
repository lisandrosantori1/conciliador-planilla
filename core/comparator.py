"""Lógica de conciliación entre dos DataFrames."""

import pandas as pd


def conciliar(df_a, df_b, key_mappings, compare_mappings, keep_b_keys=False):
    """
    Realiza la conciliación entre dos DataFrames con mapeo flexible de columnas.

    Args:
        key_mappings:     Lista de {"col_a", "col_b", "fuzzy"} que identifican coincidencias.
        compare_mappings: Lista de {"col_a", "col_b"} donde detectar diferencias.
        keep_b_keys:      Si True, agrega las columnas clave de Tabla B en coincidencias.

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

    # Si renombrar col_b → col_a crearía duplicados (ej: df_b tiene "Pepito" y "Pepito.1",
    # se mapea A."Pepito" ↔ B."Pepito.1"), hay que eliminar primero la col existente con
    # ese nombre, siempre que no sea en sí misma un col_b en otro mapeo.
    all_col_b_names = {m["col_b"] for m in key_mappings + compare_mappings}
    cols_to_drop = [
        col_a for col_b, col_a in rename_b.items()
        if col_a in df_b.columns and col_a not in all_col_b_names
    ]
    df_b_aligned = df_b.drop(columns=cols_to_drop).rename(columns=rename_b)
    compare_cols = [m["col_a"] for m in compare_mappings]

    normalize_cols = {m["col_a"] for m in key_mappings if m.get("normalize")}

    if has_fuzzy:
        fuzzy_cols = {m["col_a"] for m in key_mappings if m.get("fuzzy")}
        coincidencias, solo_a, solo_b = _fuzzy_merge(
            df_a, df_b_aligned, key_cols_a, fuzzy_cols, compare_cols, normalize_cols
        )
        if keep_b_keys and not coincidencias.empty and "__b_matched_idx__" in coincidencias.columns:
            b_orig = df_b.reset_index(drop=True)
            for m in key_mappings:
                col_a, col_b_orig = m["col_a"], m["col_b"]
                b_display = col_b_orig if col_b_orig != col_a else f"{col_a}_B"
                if b_display not in coincidencias.columns:
                    b_idxs = coincidencias["__b_matched_idx__"].tolist()
                    pos = list(coincidencias.columns).index(col_a) + 1
                    coincidencias.insert(pos, b_display, b_orig.loc[b_idxs, col_b_orig].values)
        coincidencias = coincidencias.drop(columns=["__b_matched_idx__"], errors="ignore")
    else:
        # Merge exacto con normalización de separador decimal
        df_a_work = df_a.copy()
        df_b_work = df_b_aligned.copy()

        if keep_b_keys:
            df_b_work["__bidx__"] = range(len(df_b_work))

        for col in key_cols_a:
            fn = _normalize_id_col if col in normalize_cols else _normalize_key_col
            df_a_work[col] = fn(df_a_work[col])
            df_b_work[col] = fn(df_b_work[col])

        df_merge = pd.merge(
            df_a_work, df_b_work,
            on=key_cols_a,
            how="outer",
            suffixes=("_A", "_B"),
            indicator=True,
        )
        coincidencias = df_merge[df_merge["_merge"] == "both"].copy()
        solo_a = df_merge[df_merge["_merge"] == "left_only"].copy()
        solo_b = df_merge[df_merge["_merge"] == "right_only"].copy()

        if keep_b_keys and "__bidx__" in coincidencias.columns:
            b_orig = df_b.reset_index(drop=True)
            for m in key_mappings:
                col_a, col_b_orig = m["col_a"], m["col_b"]
                b_display = col_b_orig if col_b_orig != col_a else f"{col_a}_B"
                if b_display not in coincidencias.columns:
                    bidx = coincidencias["__bidx__"].astype(int).tolist()
                    pos = list(coincidencias.columns).index(col_a) + 1
                    coincidencias.insert(pos, b_display, b_orig.loc[bidx, col_b_orig].values)
            for df in [coincidencias, solo_a, solo_b]:
                df.drop(columns=["__bidx__"], inplace=True, errors="ignore")

    diferencias = _find_differences(coincidencias, compare_mappings, key_cols_a)
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


def _find_fuzzy_pairs(df_a, df_b, key_cols, fuzzy_cols, normalize_cols=None):
    """Encuentra pares (idx_a, idx_b) que coinciden según las reglas de cada columna clave.

    Para columnas exactas normaliza el separador decimal.
    Para columnas fuzzy hace strip y verifica contenido.
    Para columnas normalize elimina guiones/espacios (CUIT/DNI).
    Cada fila de A se une con a lo sumo una fila de B (primera coincidencia).
    """
    normalize_cols = normalize_cols or set()
    a_vals = {}
    b_vals = {}
    for col in key_cols:
        if col in normalize_cols:
            a_vals[col] = [_normalize_id_scalar(v) for v in df_a[col]]
            b_vals[col] = [_normalize_id_scalar(v) for v in df_b[col]]
        elif col in fuzzy_cols:
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


def _fuzzy_merge(df_a, df_b, key_cols, fuzzy_cols, compare_cols, normalize_cols=None):
    """Construye coincidencias, solo_a y solo_b usando fuzzy matching."""
    pairs = _find_fuzzy_pairs(df_a, df_b, key_cols, fuzzy_cols, normalize_cols)

    matched_a = [p[0] for p in pairs]
    matched_b = [p[1] for p in pairs]
    matched_a_set = set(matched_a)
    matched_b_set = set(matched_b)

    if pairs:
        rows_a = df_a.loc[matched_a].reset_index(drop=True)
        rows_b = df_b.loc[matched_b].reset_index(drop=True)

        for col in fuzzy_cols:
            if col in rows_a.columns:
                rows_a[col] = rows_a[col].astype(str).str.strip()

        b_non_key = [c for c in df_b.columns if c not in key_cols]
        a_non_key = [c for c in df_a.columns if c not in key_cols]
        conflict = set(a_non_key) & set(b_non_key)

        rows_a_out = rows_a.rename(columns={c: f"{c}_A" for c in conflict})
        rows_b_out = rows_b[b_non_key].rename(columns={c: f"{c}_B" for c in conflict})

        coincidencias = pd.concat([rows_a_out, rows_b_out], axis=1)
        coincidencias["_merge"] = "both"
        coincidencias["__b_matched_idx__"] = matched_b

        # Para columnas clave que también están en compare_cols, agregar _A y _B
        # para que _find_differences pueda comparar los valores originales de ambas tablas
        key_cols_in_compare = [c for c in key_cols if c in set(compare_cols or [])]
        for col in key_cols_in_compare:
            if col in coincidencias.columns and f"{col}_A" not in coincidencias.columns:
                coincidencias[f"{col}_A"] = coincidencias[col].values
            if col in rows_b.columns and f"{col}_B" not in coincidencias.columns:
                coincidencias[f"{col}_B"] = rows_b[col].values
    else:
        coincidencias = pd.DataFrame()

    solo_a = df_a.loc[~df_a.index.isin(matched_a_set)].copy()
    solo_a["_merge"] = "left_only"

    solo_b = df_b.loc[~df_b.index.isin(matched_b_set)].copy()
    solo_b["_merge"] = "right_only"

    return coincidencias, solo_a, solo_b


# ── Normalización decimal ──────────────────────────────────────────────────────

def _try_to_date(val) -> str | None:
    """Parsea un valor como fecha y retorna 'YYYY-MM-DD', o None si no es fecha.

    Reconoce formatos DD/MM/YYYY, D/M/YYYY HH:MM:SS, YYYY-MM-DD, etc.
    Usa dayfirst=True (convención argentina DD/MM/YYYY).
    """
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", ""):
        return None
    # Solo intentar si hay separadores típicos de fecha (/ o -)
    if "/" not in s and "-" not in s:
        return None
    try:
        # Formato ISO (YYYY-MM-DD): no necesita dayfirst
        if s[:4].isdigit() and len(s) >= 8 and s[4] == "-":
            dt = pd.to_datetime(s)
        else:
            dt = pd.to_datetime(s, dayfirst=True)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError, OverflowError):
        return None


def _normalize_scalar(val) -> str:
    """Versión escalar de normalización para uso en listas."""
    if pd.isna(val):
        return ""
    s = str(val).strip()
    f = _try_to_float(s)
    if f is not None:
        return str(int(f)) if f == int(f) else f"{f:.10g}"
    d = _try_to_date(s)
    if d is not None:
        return d
    return s


def _normalize_key_col(series: pd.Series) -> pd.Series:
    """Normaliza una columna clave unificando el separador decimal antes del merge."""
    return series.apply(_normalize_scalar)


def _normalize_id_scalar(val) -> str:
    """Normalización para IDs con guiones (CUIT/DNI): elimina guiones/espacios si el resultado es numérico.
    Para valores que no son IDs numéricos (ej: fechas) cae a normalización estándar.
    """
    if pd.isna(val):
        return ""
    s = str(val).strip()
    stripped = s.replace("-", "").replace(" ", "")
    if stripped.isdigit() and stripped:
        return stripped
    # Fechas con / o -: normalizar a YYYY-MM-DD para comparar independientemente del formato
    d = _try_to_date(s)
    if d is not None:
        return d
    f = _try_to_float(s)
    if f is not None:
        return str(int(f)) if f == int(f) else f"{f:.10g}"
    return s


def _normalize_id_col(series: pd.Series) -> pd.Series:
    """Normalización de columna clave para CUIT/DNI: elimina guiones antes del merge."""
    return series.apply(_normalize_id_scalar)


def _try_to_float(val) -> float | None:
    """Parsea un valor como float tolerando coma o punto como separador decimal."""
    v = str(val).strip()
    if not v or v.lower() in ("nan", "none", ""):
        return None

    has_comma = "," in v
    has_dot = "." in v

    try:
        if has_comma and has_dot:
            if v.rindex(",") > v.rindex("."):
                v = v.replace(".", "").replace(",", ".")
            else:
                v = v.replace(",", "")
        elif has_comma:
            v = v.replace(",", ".")
        return float(v)
    except (ValueError, AttributeError):
        return None


# ── Detección de diferencias ───────────────────────────────────────────────────

def _values_differ(a_val, b_val) -> bool:
    """Compara dos valores considerando formatos decimales y de fecha equivalentes."""
    a_str = str(a_val).strip()
    b_str = str(b_val).strip()
    if a_str == b_str:
        return False
    a_f = _try_to_float(a_str)
    b_f = _try_to_float(b_str)
    if a_f is not None and b_f is not None:
        return a_f != b_f
    a_d = _try_to_date(a_str)
    b_d = _try_to_date(b_str)
    if a_d is not None and b_d is not None:
        return a_d != b_d
    return a_str != b_str


def _find_differences(coincidencias, compare_mappings, key_cols):
    """Detecta filas con diferencias usando comparación vectorizada por columna.

    compare_mappings: lista de {"col_a", "col_b", "fuzzy", "normalize"}.
    Si fuzzy=True considera iguales cuando uno contiene al otro.
    Si normalize=True elimina guiones/espacios antes de comparar.
    """
    if not compare_mappings or coincidencias.empty:
        return pd.DataFrame()

    compare_cols = [m["col_a"] for m in compare_mappings]

    diff_flags = {}
    for m in compare_mappings:
        col = m["col_a"]
        fuzzy = m.get("fuzzy", False)
        normalize_flag = m.get("normalize", False)
        col_a_name = f"{col}_A"
        col_b_name = f"{col}_B"
        if col_a_name not in coincidencias.columns or col_b_name not in coincidencias.columns:
            continue
        a = coincidencias[col_a_name]
        b = coincidencias[col_b_name]
        both_null = a.isna() & b.isna()
        if fuzzy:
            str_diff = pd.Series(
                [not _fuzzy_key_match(str(av), str(bv))
                 for av, bv in zip(a.fillna(""), b.fillna(""))],
                index=a.index, dtype=bool,
            )
        elif normalize_flag:
            str_diff = pd.Series(
                [_normalize_id_scalar(av) != _normalize_id_scalar(bv)
                 for av, bv in zip(a.fillna(""), b.fillna(""))],
                index=a.index, dtype=bool,
            )
        else:
            str_diff = pd.Series(
                [_values_differ(av, bv) for av, bv in zip(a.fillna(""), b.fillna(""))],
                index=a.index, dtype=bool,
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
