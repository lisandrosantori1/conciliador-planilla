"""
Módulo para detectar automáticamente tipos de datos en columnas.
 
Detecta si una columna es: int, float, date o str
usando muestreo inteligente de múltiples valores.
"""
 
import pandas as pd
from typing import Literal
 
 
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
            try:
                pd.to_datetime(val)
            except (ValueError, TypeError):
                raise ValueError("not a date")
        return "date"
    except (ValueError, TypeError, AttributeError):
        return "str"
