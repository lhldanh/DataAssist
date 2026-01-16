from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, Any, List

def _series_missing_info(s: pd.Series) -> Dict[str, Any]:
    missing = int(s.isna().sum())
    total = int(len(s))
    return {
        "missing": missing,
        "missing_pct": float(missing / total) if total else 0.0,
        "non_null": int(total - missing),
    }

def _top_values(s: pd.Series, k: int = 5) -> List[Dict[str, Any]]:
    # Convert to string for stable display, keep NaN separate
    vc = s.dropna().astype(str).value_counts().head(k)
    return [{"value": idx, "count": int(cnt)} for idx, cnt in vc.items()]

def profile_dataset(df: pd.DataFrame, top_k: int = 5) -> Dict[str, Any]:
    """
    Return a compact EDA profile dict safe to show/serialize.
    """
    n_rows, n_cols = df.shape

    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
    missing_by_col = {col: _series_missing_info(df[col]) for col in df.columns}

    duplicate_rows = int(df.duplicated().sum())

    # Numeric stats
    num_df = df.select_dtypes(include=[np.number])
    numeric_stats = {}
    if not num_df.empty:
        desc = num_df.describe(percentiles=[0.25, 0.5, 0.75]).transpose()
        for col, row in desc.iterrows():
            numeric_stats[col] = {
                "count": float(row.get("count", np.nan)),
                "mean": float(row.get("mean", np.nan)),
                "std": float(row.get("std", np.nan)),
                "min": float(row.get("min", np.nan)),
                "p25": float(row.get("25%", np.nan)),
                "median": float(row.get("50%", np.nan)),
                "p75": float(row.get("75%", np.nan)),
                "max": float(row.get("max", np.nan)),
            }

    # Categorical summary
    cat_cols = [c for c in df.columns if dtypes[c] == "object" or "category" in dtypes[c]]
    categorical_summary = {}
    for col in cat_cols:
        s = df[col]
        categorical_summary[col] = {
            "unique": int(s.nunique(dropna=True)),
            "top_values": _top_values(s, k=top_k),
        }

    # Overall missing
    total_cells = int(n_rows * n_cols) if n_rows and n_cols else 0
    total_missing = int(df.isna().sum().sum())
    overall_missing_pct = float(total_missing / total_cells) if total_cells else 0.0

    return {
        "shape": {"rows": int(n_rows), "cols": int(n_cols)},
        "dtypes": dtypes,
        "missing_by_col": missing_by_col,
        "duplicates": {"duplicate_rows": duplicate_rows},
        "missing_overall": {"total_missing": total_missing, "missing_pct": overall_missing_pct},
        "numeric_stats": numeric_stats,
        "categorical_summary": categorical_summary,
    }
