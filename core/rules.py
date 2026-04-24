def cast_value(value, dtype):
    import pandas as pd
    
    try:
        if dtype == "int":
            return int(value)
        elif dtype == "float":
            return float(value)
        elif dtype == "date":
            series = pd.to_datetime(series, errors="coerce")
            value = pd.to_datetime(value, errors="coerce")
    except:
        return value
    
    return value


def apply_rule(series, rule, value=None, value2=None, dtype="str"):
    
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
        return series.astype(str).str.contains(value, na=False)
    
    elif rule == "starts_with":
        return series.astype(str).str.startswith(value, na=False)

    elif rule == "between":
        if value is None or value2 is None:
            return None
        return (series >= value) & (series <= value2)

    elif rule == "is_null":
        return series.isna()

    elif rule == "not_null":
        return series.notna()

    return None