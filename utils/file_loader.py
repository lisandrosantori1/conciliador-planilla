"""Utilidades para cargar archivos Excel y CSV con caché."""

import pandas as pd
import streamlit as st
from io import BytesIO

_EXCEL_EXTENSIONS = (".xlsx", ".xls", ".xlsm", ".xlsb")


def _is_excel(file_name: str) -> bool:
    return file_name.lower().endswith(_EXCEL_EXTENSIONS)


def _excel_engine(file_name: str) -> str:
    """Retorna el engine correcto según la extensión."""
    name = file_name.lower()
    if name.endswith(".xls"):
        return "xlrd"
    if name.endswith(".xlsb"):
        return "pyxlsb"
    return "openpyxl"


@st.cache_data(show_spinner=False)
def load_dataframe(
    file_content: bytes,
    file_name: str,
    sheet: str = None,
    decimal: str = "."
) -> pd.DataFrame:
    """Carga un archivo Excel o CSV desde bytes en un DataFrame.

    Args:
        decimal: Separador decimal para CSV ('.' o ','). Ignorado en Excel.
    """
    if _is_excel(file_name):
        engine = _excel_engine(file_name)
        return pd.read_excel(BytesIO(file_content), sheet_name=sheet, engine=engine)
    return pd.read_csv(BytesIO(file_content), decimal=decimal, sep=None, engine="python")


@st.cache_data(show_spinner=False)
def get_excel_sheets(file_content: bytes, file_name: str) -> list:
    """Retorna los nombres de las hojas de un archivo Excel."""
    engine = _excel_engine(file_name)
    return pd.ExcelFile(BytesIO(file_content), engine=engine).sheet_names


def accepted_extensions() -> list:
    """Lista de extensiones aceptadas por los file uploaders."""
    return ["xlsx", "xls", "xlsm", "csv"]
