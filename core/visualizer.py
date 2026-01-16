from __future__ import annotations
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional

def fig_hist(df: pd.DataFrame, col: str, bins: int = 30):
    s = df[col].dropna()
    fig, ax = plt.subplots()
    ax.hist(s, bins=bins)
    ax.set_title(f"Histogram: {col}")
    ax.set_xlabel(col)
    ax.set_ylabel("Count")
    return fig

def fig_bar_topk(df: pd.DataFrame, col: str, k: int = 20):
    s = df[col].dropna().astype(str)
    vc = s.value_counts().head(k)
    fig, ax = plt.subplots()
    ax.bar(vc.index, vc.values)
    ax.set_title(f"Top {k} values: {col}")
    ax.set_xlabel(col)
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", labelrotation=45)
    fig.tight_layout()
    return fig

def fig_line_timeseries(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    freq: str = "M",
    agg: str = "sum",
):
    """
    freq: 'D','W','M','Q'...
    """
    d = df[[date_col, value_col]].copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col])
    if d.empty:
        raise ValueError("No valid datetime values found.")

    d = d.set_index(date_col)
    if agg == "sum":
        ts = d[value_col].resample(freq).sum()
    elif agg == "mean":
        ts = d[value_col].resample(freq).mean()
    elif agg == "count":
        ts = d[value_col].resample(freq).count()
    else:
        raise ValueError("agg must be one of: sum, mean, count")

    fig, ax = plt.subplots()
    ax.plot(ts.index, ts.values)
    ax.set_title(f"{agg}({value_col}) over time ({freq})")
    ax.set_xlabel("Time")
    ax.set_ylabel(value_col)
    fig.tight_layout()
    return fig

def fig_scatter(df: pd.DataFrame, x: str, y: str):
    d = df[[x, y]].dropna()
    fig, ax = plt.subplots()
    ax.scatter(d[x], d[y])
    ax.set_title(f"Scatter: {x} vs {y}")
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    fig.tight_layout()
    return fig

def fig_corr_heatmap(df: pd.DataFrame, max_cols: int = 25):
    num = df.select_dtypes(include=[np.number])
    if num.shape[1] < 2:
        raise ValueError("Need at least 2 numeric columns for correlation heatmap.")

    # limit columns to keep readable
    if num.shape[1] > max_cols:
        num = num.iloc[:, :max_cols]

    corr = num.corr(numeric_only=True)

    fig, ax = plt.subplots()
    im = ax.imshow(corr.values, aspect="auto")
    ax.set_title("Correlation Heatmap")
    ax.set_xticks(range(corr.shape[1]))
    ax.set_yticks(range(corr.shape[0]))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticklabels(corr.index)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return fig
