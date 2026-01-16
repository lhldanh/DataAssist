import json
import numpy as np
import pandas as pd
import streamlit as st

from core.visualizer import (
    fig_hist, fig_bar_topk, fig_scatter, fig_corr_heatmap, fig_line_timeseries
)
from app.components.charts import show_fig_centered, save_png_bytes
from core.chart_summary import (
    summarize_hist, summarize_topk_bar, summarize_scatter
)
from llm.client import call_llm
from llm.prompts import CHART_INSIGHT_PROMPT

st.title("Visualize")

df = st.session_state.get("df")
if df is None:
    st.warning("Please upload a dataset first.")
    st.stop()

# --------------------------
# Auto-clear insight on change
# --------------------------
def chart_signature(chart_type: str, params: dict) -> str:
    items = tuple(sorted(params.items()))
    return f"{chart_type}::{items}"

def auto_clear_insight_if_changed(sig: str):
    prev = st.session_state.get("_chart_sig")
    if prev != sig:
        st.session_state["_chart_sig"] = sig
        st.session_state.pop("chart_insight", None)

# --------------------------
# UI controls
# --------------------------
chart_type = st.selectbox(
    "Chart type",
    ["Histogram", "Top-K Bar", "Scatter", "Correlation Heatmap", "Time Series Line"]
)
img_width = st.slider("Chart width (px)", 320, 900, 520, 20)

art_dir = "artifacts/charts"

# --------------------------
# Actions (Save / Analyze)
# --------------------------
def render_actions(png_bytes: bytes, filename_prefix: str, summary: dict, chart_key: str):
    # spacer | save | analyze  (Analyze will be at far right)
    c1, spacer, c2 = st.columns([2, 6, 2])

    with c1:
        if st.button("💾 Save chart", key=f"save_{chart_key}"):
            path = save_png_bytes(png_bytes, save_dir=art_dir, filename_prefix=filename_prefix)
            st.success(f"Saved: {path}")

            # metadata store
            charts_meta = st.session_state.setdefault("charts_meta", [])
            llm_text = st.session_state.get("chart_writeups", {}).get(chart_key)

            charts_meta.append({
                "path": path,
                "chart_key": chart_key,
                "summary": summary,
                "llm_md": llm_text,
            })

            # ✅ if has LLM write-up => push to report_sections right away
            if llm_text:
                st.session_state.setdefault("report_sections", [])
                content = {
                    "type": "chart_card",
                    "path": path,
                    "llm_md": llm_text,
                    "summary": summary,
                    "title": f"Chart: {filename_prefix}"
                }
                st.session_state["report_sections"].append({
                    "title": f"Chart + LLM ({filename_prefix})",
                    "content": content
                })
                st.success("Also added this chart + LLM write-up to Report.")

    store = st.session_state.setdefault("chart_writeups", {})  # dict[chart_key] = markdown

    with c2:
        if st.button("🧠 Analyze (LLM)", key=f"analyze_{chart_key}"):
            with st.spinner("Thinking..."):
                prompt = CHART_INSIGHT_PROMPT.format(summary=json.dumps(summary, indent=2))
                store[chart_key] = call_llm(prompt)

    if store.get(chart_key):
        st.subheader("LLM Insights")
        st.markdown(store[chart_key])


# --------------------------
# Charts
# --------------------------
if chart_type == "Histogram":
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not num_cols:
        st.info("No numeric columns available for histogram.")
        st.stop()

    col = st.selectbox("Numeric column", num_cols)
    bins = st.slider("Bins", 5, 100, 30)

    params = {"col": col, "bins": bins}
    auto_clear_insight_if_changed(chart_signature("Histogram", params))

    fig = fig_hist(df, col=col, bins=bins)
    png = show_fig_centered(fig, width=img_width)

    summary = summarize_hist(df, col=col)
    render_actions(png, filename_prefix="hist", summary=summary, chart_key=f"hist_{col}")


elif chart_type == "Top-K Bar":
    col = st.selectbox("Column (categorical)", df.columns)
    k = st.slider("Top K", 5, 50, 20)

    params = {"col": col, "k": k}
    auto_clear_insight_if_changed(chart_signature("Top-K Bar", params))

    fig = fig_bar_topk(df, col=col, k=k)
    png = show_fig_centered(fig, width=img_width)

    summary = summarize_topk_bar(df, col=col, k=k)
    render_actions(png, filename_prefix="bar", summary=summary, chart_key=f"bar_{col}")


elif chart_type == "Scatter":
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(num_cols) < 2:
        st.info("Need at least 2 numeric columns for scatter.")
        st.stop()

    x = st.selectbox("X", num_cols, index=0)
    y = st.selectbox("Y", num_cols, index=1)

    params = {"x": x, "y": y}
    auto_clear_insight_if_changed(chart_signature("Scatter", params))

    fig = fig_scatter(df, x=x, y=y)
    png = show_fig_centered(fig, width=img_width)

    summary = summarize_scatter(df, x=x, y=y)
    render_actions(png, filename_prefix="scatter", summary=summary, chart_key=f"scatter_{x}_{y}")


elif chart_type == "Correlation Heatmap":
    params = {"max_width": min(img_width, 700)}
    auto_clear_insight_if_changed(chart_signature("Correlation Heatmap", params))

    try:
        fig = fig_corr_heatmap(df)
        png = show_fig_centered(fig, width=min(img_width, 700))

        summary = {
            "type": "corr_heatmap",
            "note": "Correlation heatmap for numeric columns. Use computed correlations (e.g., top pairs) for deeper insights."
        }
        render_actions(png, filename_prefix="corr", summary=summary, chart_key="corr_heatmap")

    except ValueError as e:
        st.info(str(e))


elif chart_type == "Time Series Line":
    date_col = st.selectbox("Date column", df.columns)
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not num_cols:
        st.info("No numeric columns available.")
        st.stop()

    value_col = st.selectbox("Value column", num_cols)
    freq = st.selectbox("Frequency", ["D", "W", "M", "Q"])
    agg = st.selectbox("Aggregation", ["sum", "mean", "count"])

    params = {"date_col": date_col, "value_col": value_col, "freq": freq, "agg": agg}
    auto_clear_insight_if_changed(chart_signature("Time Series Line", params))

    try:
        fig = fig_line_timeseries(df, date_col=date_col, value_col=value_col, freq=freq, agg=agg)
        png = show_fig_centered(fig, width=img_width)

        # Grounded series summary
        d = df[[date_col, value_col]].copy()
        d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
        if d.empty:
            st.info("No valid datetime values found for the selected date column.")
            st.stop()

        d = d.set_index(date_col)
        if agg == "sum":
            ts = d[value_col].resample(freq).sum()
        elif agg == "mean":
            ts = d[value_col].resample(freq).mean()
        else:
            ts = d[value_col].resample(freq).count()

        if ts.empty:
            st.info("Time series is empty after aggregation.")
            st.stop()

        summary = {
            "type": "timeseries",
            "value": value_col,
            "agg": agg,
            "freq": freq,
            "n_points": int(len(ts)),
            "start": float(ts.iloc[0]),
            "end": float(ts.iloc[-1]),
            "trend_abs": float(ts.iloc[-1] - ts.iloc[0]) if len(ts) >= 2 else 0.0,
            "peak": {"time": str(ts.idxmax().date()), "value": float(ts.max())},
            "trough": {"time": str(ts.idxmin().date()), "value": float(ts.min())},
        }

        render_actions(png, filename_prefix="ts", summary=summary, chart_key=f"ts_{date_col}_{value_col}")

    except ValueError as e:
        st.error(str(e))
