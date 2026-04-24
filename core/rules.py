"""
Módulo de reglas para filtrado y comparación de datos.
 
Define las reglas disponibles para filtrar datos según diferentes condiciones:
- equals: igualdad exacta
- not_equals: desigualdad
- greater/less: comparaciones numéricas
- contains/starts_with: búsqueda en texto
- between: rango
- is_null/not_null: validación de nulos
"""
 
import pandas as pd
from typing import Any, Optional
 
 
def cast_value(value: Any, dtype: str) -> Any:
    """Convierte un valor al tipo de dato especificado ('int', 'float', 'date', 'str')."""
    try:
        if dtype == "int":
            return int(value)
        elif dtype == "float":
            return float(value)
        elif dtype == "date":
            return pd.to_datetime(value, errors="coerce")
    except Exception:
        return value

    return value
 
 
def apply_rule(
    series: pd.Series,
    rule: str,
    value: Optional[Any] = None,
    value2: Optional[Any] = None,
    dtype: str = "str"
) -> Optional[pd.Series]:
    """
    Aplica una regla a una serie de pandas.
 
    Args:
        series: Serie de pandas a filtrar
        rule: Tipo de regla ('equals', 'greater', 'contains', etc.)
        value: Primer valor para la comparación
        value2: Segundo valor (para reglas como 'between')
        dtype: Tipo de dato de la serie
 
    Returns:
        Máscara booleana (pd.Series) o None si la regla no es válida
 
    Ejemplos:
        >>> apply_rule(df['edad'], 'greater', 18, dtype='int')
        >>> apply_rule(df['nombre'], 'contains', 'Juan', dtype='str')
    """
 
    value = cast_value(value, dtype)
    if value2:
        value2 = cast_value(value2, dtype)

    if rule == "equals":
        return series == value
    elif rule == "not_equals":
        return series != value
    elif rule == "greater":
        return series > value
    elif rule == "less":
        return series < value
    elif rule == "contains":
        return series.astype(str).str.contains(str(value), na=False, case=False)
    elif rule == "starts_with":
        return series.astype(str).str.startswith(str(value), na=False)
    elif rule == "between":
        if value is None or value2 is None:
            return None
        return (series >= value) & (series <= value2)
    elif rule == "is_null":
        return series.isna()
    elif rule == "not_null":
        return series.notna()
    elif rule == "ends_with":
        return series.astype(str).str.endswith(str(value), na=False)
    elif rule == "before":
        return pd.to_datetime(series, errors="coerce") < value
    elif rule == "after":
        return pd.to_datetime(series, errors="coerce") > value

    return None
