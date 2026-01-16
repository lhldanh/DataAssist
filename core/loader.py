# core/loader.py
from __future__ import annotations
import pandas as pd
from typing import Tuple, Dict, Any, Optional

def load_dataframe(uploaded_file, sheet_name: Optional[str] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Load CSV/XLSX to DataFrame.
    Returns (df, meta) where meta includes file type, sheet name, and basic info.
    """
    name = uploaded_file.name.lower()

    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        meta = {"file_type": "csv", "sheet": None}
        return df, meta

    if name.endswith(".xlsx") or name.endswith(".xls"):
        # If sheet_name None -> first sheet
        xls = pd.ExcelFile(uploaded_file)
        chosen = sheet_name or xls.sheet_names[0]
        df = pd.read_excel(uploaded_file, sheet_name=chosen)
        meta = {"file_type": "excel", "sheet": chosen, "sheets": xls.sheet_names}
        return df, meta

    raise ValueError("Unsupported file type. Please upload a CSV or Excel file.")