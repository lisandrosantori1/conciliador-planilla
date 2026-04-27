"""Tests para core/dtype_detector.py — detect_column_type."""

import pandas as pd
from core.dtype_detector import detect_column_type


# ── Tipos nativos de pandas ────────────────────────────────────────────────────

def test_native_int():
    assert detect_column_type(pd.Series([1, 2, 3])) == "int"

def test_native_float():
    assert detect_column_type(pd.Series([1.5, 2.3, 3.0])) == "float"

def test_native_datetime():
    s = pd.to_datetime(pd.Series(["2023-01-01", "2023-06-15"]))
    assert detect_column_type(s) == "date"


# ── Columnas object (strings) — detección numérica ────────────────────────────

def test_int_as_string():
    s = pd.Series(["100", "200", "500", "1500", "2000"])
    assert detect_column_type(s) == "int"

def test_float_as_string():
    s = pd.Series(["10.5", "20.3", "1500.8", "200.0"])
    assert detect_column_type(s) == "float"

def test_float_comma_decimal():
    s = pd.Series(["123,45", "308743,8", "1000,0"])
    assert detect_column_type(s) == "float"

def test_mixed_small_large_numbers():
    # Excel deja < 1000 como General — pandas los lee como strings
    s = pd.Series(["50", "200", "800", "1500", "3000"])
    assert detect_column_type(s) == "int"


# ── Detección de fechas ────────────────────────────────────────────────────────

def test_date_iso_format():
    s = pd.Series(["2023-01-15", "2023-06-20", "2024-01-01"])
    assert detect_column_type(s) == "date"

def test_date_slash_format():
    s = pd.Series(["15/01/2023", "20/06/2023"])
    assert detect_column_type(s) == "date"


# ── Detección de texto ─────────────────────────────────────────────────────────

def test_text_strings():
    s = pd.Series(["Juan", "Pedro", "María"])
    assert detect_column_type(s) == "str"

def test_alphanumeric_codes():
    s = pd.Series(["K46348199", "ABC-001", "X1284759AC"])
    assert detect_column_type(s) == "str"

def test_numeric_id_not_date():
    # IDs puramente numéricos no deben ser detectados como fechas
    s = pd.Series(["20123254", "46789012", "88001234"])
    result = detect_column_type(s)
    assert result in ("int", "str")  # no debe ser "date"
    assert result != "date"


# ── Casos especiales ───────────────────────────────────────────────────────────

def test_all_nulls():
    s = pd.Series([None, None, None])
    assert detect_column_type(s) == "str"

def test_nulls_with_ints():
    s = pd.Series([None, "100", None, "200"])
    assert detect_column_type(s) == "int"

def test_sample_size_respected():
    # Columna con muchos nulos al principio seguida de fechas
    s = pd.Series([None] * 5 + ["2023-01-01"] * 10)
    assert detect_column_type(s) == "date"
