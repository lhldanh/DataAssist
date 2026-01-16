from __future__ import annotations

import json
from typing import Dict, Any, List
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

from core.analyzer import top_correlations, outlier_summary_iqr, groupby_aggregate
from llm.client import call_llm
from llm.prompts import CHART_INSIGHT_PROMPT


st.title("Insights")

df = st.session_state.get("df")
if df is None:
    st.warning("Please upload a dataset first.")
    st.stop()


# --------------------------
# Session init
# --------------------------
st.session_state.setdefault("insight_history", [])          # list of snapshots
st.session_state.setdefault("insight_selected_idx", 0)      # selected snapshot index
st.session_state.setdefault("_last_gen_id", None)           # prevent double-append
st.session_state.setdefault("report_sections", [])          # report builder (optional but handy)


# --------------------------
# Helpers
# --------------------------
def sig(scope: str, params: Dict[str, Any]) -> str:
    return f"{scope}::{tuple(sorted(params.items()))}"


def df_to_md_table(df_: pd.DataFrame, max_rows: int = 10) -> str:
    """Manual Markdown table (no tabulate dependency)."""
    if df_ is None or df_.empty:
        return "_(empty table)_"
    df2 = df_.head(max_rows).copy()

    cols = [str(c) for c in df2.columns.tolist()]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"

    rows = []
    for _, r in df2.iterrows():
        vals = []
        for v in r.values:
            s = "" if pd.isna(v) else str(v)
            s = s.replace("\n", " ").replace("|", "\\|")
            vals.append(s)
        rows.append("| " + " | ".join(vals) + " |")

    return "\n".join([header, sep] + rows)


def compute_overview(df_: pd.DataFrame) -> Dict[str, Any]:
    n_rows, n_cols = df_.shape
    missing_cells = int(df_.isna().sum().sum())
    total_cells = int(n_rows * n_cols) if n_rows and n_cols else 0
    missing_pct = float(missing_cells / total_cells) if total_cells else 0.0
    dup_rows = int(df_.duplicated().sum())

    num_cols = df_.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df_.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

    return {
        "shape": {"rows": n_rows, "cols": n_cols},
        "missing": {"missing_cells": missing_cells, "missing_pct": missing_pct},
        "duplicates": {"duplicate_rows": dup_rows},
        "columns": {
            "numeric_cols": num_cols,
            "categorical_cols": cat_cols,
            "n_numeric": len(num_cols),
            "n_categorical": len(cat_cols),
        },
    }


def format_quick_findings(overview: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    miss = overview.get("missing", {})
    dups = overview.get("duplicates", {})
    shape = overview.get("shape", {})

    lines.append(f"Rows: {shape.get('rows', 0):,} | Columns: {shape.get('cols', 0):,}")
    lines.append(f"Missing: {miss.get('missing_pct', 0.0)*100:.2f}% of all cells")
    lines.append(f"Duplicate rows: {dups.get('duplicate_rows', 0):,}")
    return lines


def compute_scope_payload(
    df_: pd.DataFrame,
    scope: str,
    top_n: int,
    group_cols: List[str],
    metric_cols: List[str],
    metric_agg: str
) -> Dict[str, Any]:
    """Only scope-specific info (no quick findings here)."""
    payload: Dict[str, Any] = {"scope": scope}

    if scope in ["Overview", "Relationships (Correlations)"]:
        payload["top_correlations"] = top_correlations(df_, top_n=top_n)

    if scope in ["Overview", "Outliers (IQR)"]:
        payload["outliers_iqr"] = outlier_summary_iqr(df_)

    if scope == "Groupby Aggregation":
        if group_cols and metric_cols:
            metrics = {c: metric_agg for c in metric_cols}
            table = groupby_aggregate(df_, group_cols=group_cols, metrics=metrics, top_n=top_n)
            payload["groupby"] = {
                "group_cols": group_cols,
                "metrics": metrics,
                "preview": table.to_dict(orient="records"),
            }

    return payload


def scope_payload_to_md(scope_payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    scope = scope_payload.get("scope", "Overview")

    corrs = scope_payload.get("top_correlations") or []
    if corrs:
        lines.append("### Top correlations (abs)")
        for r in corrs[:10]:
            lines.append(f"- {r['col1']} vs {r['col2']}: **{r['abs_corr']:.3f}**")

    outd = scope_payload.get("outliers_iqr") or {}
    if outd:
        items = sorted(outd.items(), key=lambda kv: kv[1].get("outlier_pct", 0.0), reverse=True)[:10]
        lines.append("\n### Outliers (IQR)")
        for col, info in items:
            lines.append(f"- `{col}`: {info.get('outlier_pct', 0.0)*100:.2f}% outliers")

    gb = scope_payload.get("groupby")
    if gb and gb.get("preview"):
        lines.append("\n### Groupby snapshot")
        prev = pd.DataFrame(gb["preview"]).head(10)
        lines.append(df_to_md_table(prev, max_rows=10))

    if not lines:
        lines.append(f"_(No scope-specific insights generated for **{scope}**.)_")

    return "\n".join(lines)


def append_to_report(title: str, content: str):
    st.session_state.setdefault("report_sections", [])
    st.session_state["report_sections"].append({"title": title, "content": content})


# --------------------------
# Controls
# --------------------------
scope = st.selectbox(
    "Insight scope",
    ["Overview", "Relationships (Correlations)", "Outliers (IQR)", "Groupby Aggregation"],
)

top_n = st.slider("Top N (for correlations / tables)", 5, 50, 10)

group_cols: List[str] = []
metric_cols: List[str] = []
metric_agg = "sum"

if scope == "Groupby Aggregation":
    group_cols = st.multiselect(
        "Group columns",
        df.columns.tolist(),
        default=df.columns[:1].tolist() if df.shape[1] else []
    )
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    metric_cols = st.multiselect("Metric columns (numeric)", num_cols, default=num_cols[:1] if num_cols else [])
    metric_agg = st.selectbox("Aggregation", ["sum", "mean", "count", "min", "max"], index=0)

params_for_sig = {
    "scope": scope,
    "top_n": top_n,
    "group_cols": tuple(group_cols),
    "metric_cols": tuple(metric_cols),
    "agg": metric_agg,
}
current_sig = sig(scope, params_for_sig)

st.divider()

# --------------------------
# Quick findings (always current)
# --------------------------
overview_now = compute_overview(df)

# --------------------------
# Actions
# --------------------------
c1, c2, c3, c4 = st.columns([2, 2, 2, 6])
with c1:
    gen_clicked = st.button("⚙️ Generate snapshot (code)", use_container_width=True)
with c2:
    write_clicked = st.button("🧠 Write LLM for selected", use_container_width=True)
with c3:
    add_clicked = st.button("📌 Add selected to Report", use_container_width=True)
with c4:
    st.caption("Snapshots are stored in history. Overview snapshots include Quick findings; other scopes do not.")

# --------------------------
# Generate snapshot -> history (no duplicates)
# --------------------------
if gen_clicked:
    gen_id = f"{current_sig}::{datetime.now().timestamp()}"
    # prevent double-append due to rerun
    if st.session_state.get("_last_gen_id") != gen_id:
        st.session_state["_last_gen_id"] = gen_id

        scope_payload = compute_scope_payload(df, scope, top_n, group_cols, metric_cols, metric_agg)

        # computed markdown: Overview includes quick findings; others do NOT
        if scope == "Overview":
            qf_md = "### Quick findings\n" + "\n".join([f"- {x}" for x in format_quick_findings(overview_now)])
            computed_md = qf_md + "\n\n---\n\n" + scope_payload_to_md(scope_payload)
        else:
            computed_md = scope_payload_to_md(scope_payload)

        snapshot = {
            "id": gen_id,
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sig": current_sig,
            "params": {k: (list(v) if isinstance(v, tuple) else v) for k, v in params_for_sig.items()},
            "scope_payload": scope_payload,
            "computed_md": computed_md,
            "llm_md": None,
        }

        hist = st.session_state["insight_history"]

        # extra dedupe: if last snapshot is identical, skip
        if hist and hist[-1].get("sig") == current_sig and hist[-1].get("computed_md") == computed_md:
            st.info("Same snapshot detected (skipped).")
        else:
            hist.append(snapshot)
            st.session_state["insight_selected_idx"] = len(hist) - 1
            st.success("Snapshot saved to history.")
    else:
        st.info("Duplicate click detected (ignored).")

# --------------------------
# History selector
# --------------------------
hist = st.session_state.get("insight_history") or []

st.subheader("History")
if not hist:
    st.info("No snapshots yet. Click **Generate snapshot (code)**.")
    st.stop()

labels = []
for i, item in enumerate(hist):
    has_llm = "✅" if item.get("llm_md") else "—"
    labels.append(f"{i+1}. {item['ts']} | {item['params']['scope']} | LLM: {has_llm}")

selected = st.radio(
    "Select a snapshot",
    options=list(range(len(hist))),
    index=min(st.session_state.get("insight_selected_idx", 0), len(hist) - 1),
    format_func=lambda i: labels[i],
)
st.session_state["insight_selected_idx"] = selected

snap = hist[selected]
scope_payload = snap["scope_payload"]

# --------------------------
# Show selected snapshot
# --------------------------
st.subheader("Selected snapshot (computed)")

with st.expander("Computed markdown (what goes into report)", expanded=True):
    st.markdown(snap["computed_md"])

with st.expander("Raw JSON (debug)", expanded=False):
    st.code(json.dumps(scope_payload, indent=2), language="json")

st.divider()

# --------------------------
# LLM options
# --------------------------
st.subheader("LLM write-up options")
include_llm = st.checkbox("Include LLM write-up when adding to report", value=False)
append_llm_to_computed = st.checkbox("Append LLM write-up into computed section (single section)", value=True)

# Write LLM for selected snapshot (saved into that snapshot)
if write_clicked:
    with st.spinner("Thinking..."):
        prompt = CHART_INSIGHT_PROMPT.format(summary=json.dumps(scope_payload, indent=2))
        llm_md = call_llm(prompt)
        st.session_state["insight_history"][selected]["llm_md"] = llm_md
    st.success("LLM write-up saved for this snapshot.")

llm_text = st.session_state["insight_history"][selected].get("llm_md")
if llm_text:
    st.subheader("LLM write-up (saved)")
    st.markdown(llm_text)
else:
    st.caption("No LLM write-up saved for this snapshot yet.")

# --------------------------
# Add selected snapshot to report
# --------------------------
if add_clicked:
    computed = snap.get("computed_md") or ""
    llm_md = snap.get("llm_md")

    title_base = f"Insights ({snap['params']['scope']})"

    if include_llm and llm_md:
        if append_llm_to_computed:
            content = computed + "\n\n---\n\n### LLM write-up\n\n" + llm_md
            append_to_report(title_base, content)
        else:
            append_to_report(title_base, computed)
            append_to_report(title_base + " (LLM)", llm_md)
    else:
        append_to_report(title_base, computed)

    st.success("Added selected snapshot to report.")
