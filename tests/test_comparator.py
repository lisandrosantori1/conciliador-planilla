"""Tests para core/comparator.py — conciliar, _find_differences, fuzzy matching."""

import pandas as pd
import pytest
from core.comparator import _fuzzy_key_match, _try_to_float, _values_differ, conciliar


# ── _try_to_float ──────────────────────────────────────────────────────────────

def test_try_to_float_dot():
    assert _try_to_float("308743.8") == 308743.8

def test_try_to_float_comma():
    assert _try_to_float("308743,8") == 308743.8

def test_try_to_float_european_thousands():
    assert _try_to_float("1.234,56") == 1234.56

def test_try_to_float_us_thousands():
    assert _try_to_float("1,234.56") == 1234.56

def test_try_to_float_text():
    assert _try_to_float("ABC") is None

def test_try_to_float_empty():
    assert _try_to_float("") is None

def test_try_to_float_nan():
    assert _try_to_float("nan") is None


# ── _values_differ ─────────────────────────────────────────────────────────────

def test_values_differ_equal_dot_comma():
    assert _values_differ("308743.8", "308743,8") is False

def test_values_differ_truly_different():
    assert _values_differ("308743.8", "308743.9") is True

def test_values_differ_text_equal():
    assert _values_differ("Juan", "Juan") is False

def test_values_differ_text_different():
    assert _values_differ("Juan", "Pedro") is True


# ── _fuzzy_key_match ───────────────────────────────────────────────────────────

def test_fuzzy_prefix_k():
    assert _fuzzy_key_match("46348199", "K46348199") is True

def test_fuzzy_prefix_k_reversed():
    assert _fuzzy_key_match("K68225187AB", "68225187AB") is True

def test_fuzzy_with_spaces():
    assert _fuzzy_key_match("04589914AF   ", "K04589914AF") is True

def test_fuzzy_no_match():
    assert _fuzzy_key_match("12345678", "87654321") is False

def test_fuzzy_too_short():
    # Valores menores a 3 chars no hacen fuzzy para evitar falsos positivos
    assert _fuzzy_key_match("AB", "XABZ") is False


# ── conciliar — merge exacto ───────────────────────────────────────────────────

@pytest.fixture
def simple_tables():
    df_a = pd.DataFrame({"id": [1, 2, 3, 4], "valor_a": [10, 20, 30, 40]})
    df_b = pd.DataFrame({"id": [1, 2, 3, 5], "valor_b": [10, 20, 99, 50]})
    return df_a, df_b

def test_coincidencias_count(simple_tables):
    df_a, df_b = simple_tables
    km = [{"col_a": "id", "col_b": "id", "fuzzy": False}]
    coinc, solo_a, solo_b, difs = conciliar(df_a, df_b, km, [])
    assert len(coinc) == 3
    assert len(solo_a) == 1  # id=4
    assert len(solo_b) == 1  # id=5

def test_differences_detected(simple_tables):
    df_a, df_b = simple_tables
    km = [{"col_a": "id", "col_b": "id", "fuzzy": False}]
    cm = [{"col_a": "valor_a", "col_b": "valor_b"}]
    _, _, _, difs = conciliar(df_a, df_b, km, cm)
    # id=3: valor_a=30 vs valor_b=99 → diferencia
    # _normalize_key_col convierte los ids a string ("3") para el merge
    assert len(difs) == 1
    assert str(difs.iloc[0]["id"]) == "3"

def test_no_differences_when_equal():
    df_a = pd.DataFrame({"id": [1, 2], "precio": [100.0, 200.0]})
    df_b = pd.DataFrame({"id": [1, 2], "precio": [100.0, 200.0]})
    km = [{"col_a": "id", "col_b": "id", "fuzzy": False}]
    cm = [{"col_a": "precio", "col_b": "precio"}]
    _, _, _, difs = conciliar(df_a, df_b, km, cm)
    assert len(difs) == 0


# ── conciliar — normalización decimal en columna clave ────────────────────────

def test_key_decimal_normalization():
    df_a = pd.DataFrame({"codigo": ["123,45", "200.0"], "v": [1, 2]})
    df_b = pd.DataFrame({"codigo": ["123.45", "200"],   "v": [1, 2]})
    km = [{"col_a": "codigo", "col_b": "codigo", "fuzzy": False}]
    coinc, solo_a, solo_b, _ = conciliar(df_a, df_b, km, [])
    assert len(coinc) == 2
    assert len(solo_a) == 0
    assert len(solo_b) == 0


# ── conciliar — diferencias con decimal normalizado ───────────────────────────

def test_differences_decimal_normalization():
    # 308743.8 y 308743,8 son el mismo valor → no diferencia
    df_a = pd.DataFrame({"id": [1], "precio": ["308743.8"]})
    df_b = pd.DataFrame({"id": [1], "precio": ["308743,8"]})
    km = [{"col_a": "id", "col_b": "id", "fuzzy": False}]
    cm = [{"col_a": "precio", "col_b": "precio"}]
    _, _, _, difs = conciliar(df_a, df_b, km, cm)
    assert len(difs) == 0


# ── conciliar — column name mapping ───────────────────────────────────────────

def test_different_column_names():
    df_a = pd.DataFrame({"dni": [1, 2, 3]})
    df_b = pd.DataFrame({"documento": [1, 2, 4]})
    km = [{"col_a": "dni", "col_b": "documento", "fuzzy": False}]
    coinc, solo_a, solo_b, _ = conciliar(df_a, df_b, km, [])
    assert len(coinc) == 2
    assert len(solo_a) == 1
    assert len(solo_b) == 1


# ── conciliar — fuzzy matching ─────────────────────────────────────────────────

def test_fuzzy_merge():
    df_a = pd.DataFrame({"cod": ["46348199", "K68225187AB", "NOMATCHA"]})
    df_b = pd.DataFrame({"cod": ["K46348199", "68225187AB",  "NOMATCHB"]})
    km = [{"col_a": "cod", "col_b": "cod", "fuzzy": True}]
    coinc, solo_a, solo_b, _ = conciliar(df_a, df_b, km, [])
    assert len(coinc) == 2
    assert len(solo_a) == 1
    assert len(solo_b) == 1


# ── conciliar — tablas vacías ──────────────────────────────────────────────────

def test_empty_compare_cols():
    df_a = pd.DataFrame({"id": [1, 2]})
    df_b = pd.DataFrame({"id": [1, 2]})
    km = [{"col_a": "id", "col_b": "id", "fuzzy": False}]
    coinc, _, _, difs = conciliar(df_a, df_b, km, [])
    assert len(coinc) == 2
    assert difs.empty
