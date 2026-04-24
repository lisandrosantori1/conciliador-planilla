"""
Módulo para detectar automáticamente tipos de datos en columnas.

Detecta si una columna es: int, float, date o str
usando muestreo inteligente de múltiples valores.
"""

import re
import pandas as pd
from typing import Literal

# Patrón que exige al menos un separador de fecha o formato ISO (YYYY-MM-DD, DD/MM/YYYY, etc.)
# Rechaza strings puramente numéricos como "20123254" que pandas puede parsear como fecha.
_DATE_PATTERN = re.compile(
    r'\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4}'   # YYYY-MM-DD, DD/MM/YYYY, etc.
    r'|\d{1,2}\s+\w+\s+\d{4}'               # "15 enero 2023"
)

VALID_TYPES = ["str", "int", "float", "date"]


def _looks_like_date_string(val) -> bool:
    """Retorna True solo si el string tiene estructura reconocible de fecha con separadores."""
    return bool(_DATE_PATTERN.search(str(val).strip()))


def detect_column_type(
    series: pd.Series,
    sample_size: int = 10
) -> Literal["int", "float", "date", "str"]:
    """Detecta el tipo de dato de una columna muestreando múltiples valores no-nulos."""

    if pd.api.types.is_integer_dtype(series):
        return "int"
    if pd.api.types.is_float_dtype(series):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"

    non_null_values = series.dropna()
    if len(non_null_values) == 0:
        return "str"

    sample = non_null_values.head(sample_size)

    try:
        for val in sample:
            # Rechazar valores que no tienen estructura visual de fecha
            if not _looks_like_date_string(val):
                raise ValueError("not a date")
            try:
                pd.to_datetime(val)
            except (ValueError, TypeError):
                raise ValueError("not a date")
        return "date"
    except (ValueError, TypeError, AttributeError):
        return "str"
