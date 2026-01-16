from __future__ import annotations
import streamlit as st
import pandas as pd
from typing import Optional

def show_df(df: pd.DataFrame, title: Optional[str] = None, height: int = 280):
    if title:
        st.subheader(title)
    st.dataframe(df, use_container_width=True, height=height)

def dict_to_table(d: dict, key_name: str = "key", value_name: str = "value") -> pd.DataFrame:
    return pd.DataFrame([{key_name: k, value_name: v} for k, v in d.items()])

def missing_table(profile: dict, top_k: int = 15) -> pd.DataFrame:
    miss = profile.get("missing_by_col", {})
    rows = []
    for col, info in miss.items():
        rows.append({
            "column": col,
            "missing": int(info.get("missing", 0)),
            "missing_pct": float(info.get("missing_pct", 0.0)),
            "non_null": int(info.get("non_null", 0)),
        })
    df = pd.DataFrame(rows).sort_values("missing_pct", ascending=False)
    df = df[df["missing"] > 0].head(top_k)
    return df

def dtypes_table(profile: dict) -> pd.DataFrame:
    dtypes = profile.get("dtypes", {})
    return pd.DataFrame([{"column": c, "dtype": t} for c, t in dtypes.items()])

def numeric_stats_table(profile: dict, top_k: int = 15) -> pd.DataFrame:
    stats = profile.get("numeric_stats", {})
    rows = []
    for col, s in stats.items():
        rows.append({
            "column": col,
            "mean": s.get("mean"),
            "std": s.get("std"),
            "min": s.get("min"),
            "p25": s.get("p25"),
            "median": s.get("median"),
            "p75": s.get("p75"),
            "max": s.get("max"),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.head(top_k)
    return df
