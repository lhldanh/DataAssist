# core/analyzer.py
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

def top_correlations(df: pd.DataFrame, top_n: int = 10) -> List[Dict[str, Any]]:
    num = df.select_dtypes(include=[np.number])
    if num.shape[1] < 2:
        return []

    corr = num.corr(numeric_only=True).abs()
    # take upper triangle without diagonal
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    pairs = upper.stack().sort_values(ascending=False).head(top_n)

    results = []
    for (c1, c2), v in pairs.items():
        results.append({"col1": c1, "col2": c2, "abs_corr": float(v)})
    return results

def groupby_aggregate(
    df: pd.DataFrame,
    group_cols: List[str],
    metrics: Dict[str, str],
    top_n: int = 20
) -> pd.DataFrame:
    """
    metrics example: {"revenue":"sum", "quantity":"mean"}
    """
    missing_cols = [c for c in group_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Group columns not found: {missing_cols}")

    for mcol in metrics.keys():
        if mcol not in df.columns:
            raise ValueError(f"Metric column not found: {mcol}")

    out = df.groupby(group_cols, dropna=False).agg(metrics).reset_index()

    # Sort by first metric (if numeric)
    first_metric = next(iter(metrics.keys()))
    if first_metric in out.columns:
        out = out.sort_values(by=first_metric, ascending=False, na_position="last")

    return out.head(top_n)

def outlier_summary_iqr(df: pd.DataFrame, cols: Optional[List[str]] = None) -> Dict[str, Any]:
    num = df.select_dtypes(include=[np.number])
    if cols is not None:
        num = num[[c for c in cols if c in num.columns]]

    res: Dict[str, Any] = {}
    for col in num.columns:
        s = num[col].dropna()
        if s.empty:
            continue
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            res[col] = {"outliers": 0, "outlier_pct": 0.0}
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers = int(((s < lower) | (s > upper)).sum())
        res[col] = {
            "outliers": outliers,
            "outlier_pct": float(outliers / len(s)) if len(s) else 0.0,
            "lower": float(lower),
            "upper": float(upper),
        }
    return res
