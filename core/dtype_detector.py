import pandas as pd

def detect_column_type(series: pd.Series):
    if pd.api.types.is_integer_dtype(series):
        return "int"
    elif pd.api.types.is_float_dtype(series):
        return "float"
    elif pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    else:
        # Intentar parsear fechas
        try:
            pd.to_datetime(series.dropna().iloc[0])
            return "date"
        except:
            return "str"