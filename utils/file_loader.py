"""Utilidades para cargar archivos Excel y CSV con caché."""

import pandas as pd
import streamlit as st
from io import BytesIO


@st.cache_data(show_spinner=False)
def load_dataframe(file_content: bytes, file_name: str, sheet: str = None) -> pd.DataFrame:
    """Carga un archivo Excel o CSV desde bytes en un DataFrame."""
    if file_name.endswith("xlsx"):
        return pd.read_excel(BytesIO(file_content), sheet_name=sheet)
    return pd.read_csv(BytesIO(file_content))


@st.cache_data(show_spinner=False)
def get_excel_sheets(file_content: bytes) -> list:
    """Retorna los nombres de las hojas de un archivo Excel."""
    return pd.ExcelFile(BytesIO(file_content)).sheet_names
