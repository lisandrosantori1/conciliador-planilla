"""
Módulo para detectar automáticamente tipos de datos en columnas.

Detecta si una columna es: int, float, date o str
usando muestreo inteligente de múltiples valores.
"""

import re
import pandas as pd
from typing import Literal

# Exige al menos un separador de fecha (YYYY-MM-DD, DD/MM/YYYY, etc.)
# Rechaza strings puramente numéricos que pandas podría parsear como fecha.
_DATE_PATTERN = re.compile(
    r'\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4}'
    r'|\d{1,2}\s+\w+\s+\d{4}'
)

VALID_TYPES = ["str", "int", "float", "date"]


def _looks_like_date_string(val) -> bool:
    """Retorna True solo si el string tiene estructura reconocible de fecha con separadores."""
    return bool(_DATE_PATTERN.search(str(val).strip()))


def _try_numeric(val) -> float | None:
    """Intenta convertir un valor a float tolerando coma o punto como decimal."""
    v = str(val).strip()
    if not v:
        return None
    # Normalizar: si solo hay coma (sin punto) es separador decimal europeo
    if ',' in v and '.' not in v:
        v = v.replace(',', '.')
    elif ',' in v and '.' in v:
        # "1.234,56" (europeo) o "1,234.56" (anglosajón)
        if v.rindex(',') > v.rindex('.'):
            v = v.replace('.', '').replace(',', '.')
        else:
            v = v.replace(',', '')
    try:
        return float(v)
    except (ValueError, AttributeError):
        return None


def detect_column_type(
    series: pd.Series,
    sample_size: int = 15
) -> Literal["int", "float", "date", "str"]:
    """Detecta el tipo de dato de una columna muestreando hasta 15 valores no-nulos."""

    # Detección por dtype nativo de pandas (camino rápido)
    if pd.api.types.is_integer_dtype(series):
        return "int"
    if pd.api.types.is_float_dtype(series):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"

    non_null = series.dropna()
    if len(non_null) == 0:
        return "str"

    sample = non_null.head(sample_size)

    # ── Detección numérica para columnas object ────────────────────────────────
    # Excel puede dejar columnas con números < 1000 como "General" y los demás
    # como "Number", lo que hace que pandas las lea como dtype object (strings).
    numeric_vals = []
    all_numeric = True
    for val in sample:
        f = _try_numeric(val)
        if f is None:
            all_numeric = False
            break
        numeric_vals.append(f)

    if all_numeric and numeric_vals:
        if all(f == int(f) for f in numeric_vals):
            return "int"
        return "float"

    # ── Detección de fechas ────────────────────────────────────────────────────
    try:
        for val in sample:
            if not _looks_like_date_string(val):
                raise ValueError("not a date")
            try:
                pd.to_datetime(val)
            except (ValueError, TypeError):
                raise ValueError("not a date")
        return "date"
    except (ValueError, TypeError, AttributeError):
        return "str"
