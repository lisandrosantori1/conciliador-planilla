"""Tests para core/rules.py — cast_value y apply_rule."""

import pandas as pd
import pytest
from core.rules import apply_rule, cast_value


# ── cast_value ─────────────────────────────────────────────────────────────────

def test_cast_int():
    assert cast_value("42", "int") == 42
    assert cast_value(10.9, "int") == 10

def test_cast_float():
    assert cast_value("3.14", "float") == 3.14
    assert cast_value("100", "float") == 100.0

def test_cast_date():
    result = cast_value("2023-01-15", "date")
    assert pd.notna(result)
    assert str(result.date()) == "2023-01-15"

def test_cast_invalid_returns_original():
    assert cast_value("texto", "int") == "texto"
    assert cast_value("abc", "float") == "abc"

def test_cast_str_passthrough():
    assert cast_value("hello", "str") == "hello"


# ── apply_rule — numéricos ─────────────────────────────────────────────────────

@pytest.fixture
def int_series():
    return pd.Series([1, 5, 10, 20, 50])

@pytest.fixture
def float_series():
    return pd.Series([1.5, 5.0, 10.5, 20.0, 50.5])

def test_equals_int(int_series):
    result = apply_rule(int_series, "equals", 10, dtype="int")
    assert list(result) == [False, False, True, False, False]

def test_not_equals_int(int_series):
    result = apply_rule(int_series, "not_equals", 10, dtype="int")
    assert list(result) == [True, True, False, True, True]

def test_greater(int_series):
    result = apply_rule(int_series, "greater", 9, dtype="int")
    assert list(result) == [False, False, True, True, True]

def test_less(int_series):
    result = apply_rule(int_series, "less", 10, dtype="int")
    assert list(result) == [True, True, False, False, False]

def test_between(int_series):
    result = apply_rule(int_series, "between", 5, value2=20, dtype="int")
    assert list(result) == [False, True, True, True, False]

def test_between_missing_value2(int_series):
    assert apply_rule(int_series, "between", 5, dtype="int") is None


# ── apply_rule — texto ─────────────────────────────────────────────────────────

@pytest.fixture
def str_series():
    return pd.Series(["Juan García", "Pedro López", "Ana Martínez", "Juan Pérez"])

def test_contains(str_series):
    result = apply_rule(str_series, "contains", "Juan", dtype="str")
    assert list(result) == [True, False, False, True]

def test_contains_case_insensitive(str_series):
    result = apply_rule(str_series, "contains", "juan", dtype="str")
    assert list(result) == [True, False, False, True]

def test_starts_with(str_series):
    result = apply_rule(str_series, "starts_with", "Juan", dtype="str")
    assert list(result) == [True, False, False, True]

def test_ends_with(str_series):
    # "López" y "Pérez" terminan en "ez"; "García" y "Martínez" no terminan en "ópez"
    result = apply_rule(str_series, "ends_with", "ópez", dtype="str")
    assert list(result) == [False, True, False, False]


# ── apply_rule — nulos ─────────────────────────────────────────────────────────

def test_is_null():
    s = pd.Series([1, None, 3, None])
    result = apply_rule(s, "is_null")
    assert list(result) == [False, True, False, True]

def test_not_null():
    s = pd.Series([1, None, 3, None])
    result = apply_rule(s, "not_null")
    assert list(result) == [True, False, True, False]


# ── apply_rule — fechas ────────────────────────────────────────────────────────

def test_before():
    s = pd.Series(["2023-01-01", "2023-06-15", "2024-01-01"])
    result = apply_rule(s, "before", "2023-06-01", dtype="date")
    assert list(result) == [True, False, False]

def test_after():
    s = pd.Series(["2023-01-01", "2023-06-15", "2024-01-01"])
    result = apply_rule(s, "after", "2023-06-01", dtype="date")
    assert list(result) == [False, True, True]


# ── apply_rule — regla desconocida ─────────────────────────────────────────────

def test_unknown_rule_returns_none(int_series):
    assert apply_rule(int_series, "regla_inexistente", 1) is None
