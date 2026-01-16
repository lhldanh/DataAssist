from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Optional, List, Literal, Dict, Any

NumericFill = Literal["mean", "median", "min", "max"]
CatFill = Literal["mode"]
DropNAHow = Literal["any", "all", "thresh"]
KeepDup = Literal["first", "last", False]

def fill_missing(
    df: pd.DataFrame,
    numeric: NumericFill = "mean",
    categorical: CatFill = "mode",
    columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    out = df.copy()
    cols = columns if columns else out.columns.tolist()

    # numeric
    num_cols = [c for c in cols if c in out.columns and pd.api.types.is_numeric_dtype(out[c])]
    if num_cols:
        if numeric == "mean":
            vals = out[num_cols].mean(numeric_only=True)
        elif numeric == "median":
            vals = out[num_cols].median(numeric_only=True)
        elif numeric == "min":
            vals = out[num_cols].min(numeric_only=True)
        elif numeric == "max":
            vals = out[num_cols].max(numeric_only=True)
        out[num_cols] = out[num_cols].fillna(vals)

    # categorical
    cat_cols = [c for c in cols if c in out.columns and (out[c].dtype == "object" or str(out[c].dtype) == "category" or str(out[c].dtype) == "bool")]
    if cat_cols and categorical == "mode":
        for c in cat_cols:
            s = out[c]
            mode_vals = s.mode(dropna=True)
            if len(mode_vals) > 0:
                out[c] = s.fillna(mode_vals.iloc[0])

    return out

def drop_missing_rows(df: pd.DataFrame, how: DropNAHow = "any", thresh: Optional[int] = None) -> pd.DataFrame:
    if how == "thresh":
        if thresh is None:
            raise ValueError("thresh is required when how='thresh'")
        return df.dropna(thresh=thresh)
    return df.dropna(how=how)

def drop_duplicates_rows(
    df: pd.DataFrame,
    subset: Optional[List[str]] = None,
    keep: KeepDup = "first",
) -> pd.DataFrame:
    subset = subset if subset and len(subset) > 0 else None
    return df.drop_duplicates(subset=subset, keep=keep)

def summarize_cleaning(before: pd.DataFrame, after: pd.DataFrame) -> Dict[str, Any]:
    return {
        "rows_before": int(before.shape[0]),
        "rows_after": int(after.shape[0]),
        "dropped_rows": int(before.shape[0] - after.shape[0]),
        "missing_cells_before": int(before.isna().sum().sum()),
        "missing_cells_after": int(after.isna().sum().sum()),
    }
