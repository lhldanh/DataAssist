from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

def summarize_hist(df: pd.DataFrame, col: str) -> Dict[str, Any]:
    s = df[col].dropna()
    if s.empty:
        return {"type": "hist", "column": col, "note": "No non-null values."}
    return {
        "type": "hist",
        "column": col,
        "count": int(s.shape[0]),
        "min": float(s.min()),
        "max": float(s.max()),
        "mean": float(s.mean()) if pd.api.types.is_numeric_dtype(s) else None,
        "median": float(s.median()) if pd.api.types.is_numeric_dtype(s) else None,
        "std": float(s.std()) if pd.api.types.is_numeric_dtype(s) else None,
        "n_unique": int(s.nunique()),
    }

def summarize_topk_bar(df: pd.DataFrame, col: str, k: int = 20) -> Dict[str, Any]:
    s = df[col].dropna().astype(str)
    vc = s.value_counts().head(k)
    top = [{"value": idx, "count": int(cnt)} for idx, cnt in vc.items()]
    return {
        "type": "topk_bar",
        "column": col,
        "top_k": k,
        "distinct": int(s.nunique()),
        "top_values": top,
    }

def summarize_scatter(df: pd.DataFrame, x: str, y: str) -> Dict[str, Any]:
    d = df[[x, y]].dropna()
    if d.empty:
        return {"type": "scatter", "x": x, "y": y, "note": "No valid pairs."}
    corr = float(d[x].corr(d[y])) if d[x].std() and d[y].std() else None
    return {
        "type": "scatter",
        "x": x,
        "y": y,
        "n_points": int(len(d)),
        "corr": corr,
        "x_min": float(d[x].min()),
        "x_max": float(d[x].max()),
        "y_min": float(d[y].min()),
        "y_max": float(d[y].max()),
    }

def summarize_timeseries(ts_index, ts_values, value_col: str, agg: str, freq: str) -> Dict[str, Any]:
    # expects already-aggregated series from visualizer (if you want)
    s = pd.Series(ts_values, index=pd.to_datetime(ts_index))
    s = s.dropna()
    if s.empty:
        return {"type": "timeseries", "note": "Empty time series."}

    # simple trend: last - first
    trend = float(s.iloc[-1] - s.iloc[0]) if len(s) >= 2 else 0.0
    pct = float(trend / s.iloc[0]) if len(s) >= 2 and s.iloc[0] != 0 else None

    peak_t = s.idxmax()
    trough_t = s.idxmin()
    return {
        "type": "timeseries",
        "value": value_col,
        "agg": agg,
        "freq": freq,
        "n_points": int(len(s)),
        "start": float(s.iloc[0]),
        "end": float(s.iloc[-1]),
        "trend_abs": trend,
        "trend_pct": pct,
        "peak": {"time": str(peak_t.date()), "value": float(s.loc[peak_t])},
        "trough": {"time": str(trough_t.date()), "value": float(s.loc[trough_t])},
    }
