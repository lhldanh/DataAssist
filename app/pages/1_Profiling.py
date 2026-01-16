# app/pages/1_Profiling.py (or 2_Profiling.py)
import streamlit as st

from core.profiler import profile_dataset
from app.components.tables import (
    show_df, missing_table, dtypes_table, numeric_stats_table
)
from core.cleaner import (
    fill_missing, drop_missing_rows, drop_duplicates_rows, summarize_cleaning
)

st.title("Profile (EDA) & Cleaning")

# -------------------------
# Require dataset
# -------------------------
df = st.session_state.get("df")
if df is None:
    st.warning("Please upload a dataset first (Home page).")
    st.stop()

# -------------------------
# Profile cache (value-based)
# -------------------------
def refresh_profile():
    st.session_state["profile"] = profile_dataset(st.session_state["df"])

if st.session_state.get("profile") is None:
    refresh_profile()

profile = st.session_state["profile"]

# -------------------------
# Overview cards
# -------------------------
shape = profile.get("shape", {})
missing_overall = profile.get("missing_overall", {})
dups = profile.get("duplicates", {})

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", shape.get("rows", 0))
c2.metric("Columns", shape.get("cols", 0))
c3.metric("Missing (%)", f"{missing_overall.get('missing_pct', 0.0)*100:.2f}%")
c4.metric("Duplicate rows", dups.get("duplicate_rows", 0))

st.divider()

# -------------------------
# Preview
# -------------------------
with st.expander("Preview data", expanded=True):
    n = st.slider("Rows to preview", 5, 100, 20)
    show_df(st.session_state["df"].head(n), height=320)

st.divider()

# -------------------------
# Tabs
# -------------------------
tab1, tab2, tab3 = st.tabs(["Schema", "Missing values", "Numeric summary"])

with tab1:
    st.subheader("Column types")
    show_df(dtypes_table(profile), height=360)

with tab2:
    st.subheader("Top missing columns")
    miss_df = missing_table(profile, top_k=20)
    if miss_df.empty:
        st.success("No missing values detected 🎉")
    else:
        show_df(miss_df, height=360)

with tab3:
    st.subheader("Numeric statistics")
    num_df = numeric_stats_table(profile, top_k=20)
    if num_df.empty:
        st.info("No numeric columns detected.")
    else:
        show_df(num_df, height=360)

st.divider()

# -------------------------
# Data quality notes
# -------------------------
st.subheader("Data quality notes")
notes = []

miss_pct = float(missing_overall.get("missing_pct", 0.0))
if miss_pct > 0.1:
    notes.append(f"High missing rate: {miss_pct*100:.2f}% of all cells are missing.")

dup_n = int(dups.get("duplicate_rows", 0))
if dup_n > 0:
    notes.append(f"Found {dup_n} duplicate rows (consider deduplication).")

cat_sum = profile.get("categorical_summary", {})
for col, info in cat_sum.items():
    uniq = int(info.get("unique", 0))
    if uniq > 200:
        notes.append(f"High-cardinality column `{col}`: {uniq} unique values (may need grouping).")

if notes:
    for n in notes:
        st.write(f"- {n}")
else:
    st.write("- No major data quality issues detected from basic checks.")

# -------------------------
# Quick cleaning (optional hook)
# -------------------------
with st.expander("Quick cleaning", expanded=False):
    left, right = st.columns(2)

    with left:
        st.markdown("### Missing values")
        action = st.radio("Action", ["Fill missing", "Drop missing rows"], horizontal=True)

        if action == "Fill missing":
            num_strategy = st.selectbox("Numeric fill", ["mean", "median", "min", "max"], index=0)
            if st.button("Apply fill", use_container_width=True):
                before = st.session_state["df"]
                after = fill_missing(before, numeric=num_strategy, categorical="mode")
                st.session_state["df"] = after
                refresh_profile()
                st.success(str(summarize_cleaning(before, after)))

        else:
            mode = st.selectbox("Drop mode", ["any", "all", "thresh"], index=0)
            thresh = None
            if mode == "thresh":
                thresh = st.slider(
                    "Keep rows with at least N non-null values",
                    1, st.session_state["df"].shape[1],
                    min(st.session_state["df"].shape[1], max(1, st.session_state["df"].shape[1] - 1))
                )
            if st.button("Drop rows", use_container_width=True):
                before = st.session_state["df"]
                after = drop_missing_rows(before, how=mode, thresh=thresh)
                st.session_state["df"] = after
                refresh_profile()
                st.success(str(summarize_cleaning(before, after)))

    with right:
        st.markdown("### Duplicates")
        keep = st.selectbox("Keep", ["first", "last", False], index=0)
        subset_cols = st.multiselect("Subset columns (optional)", st.session_state["df"].columns.tolist())

        if st.button("Drop duplicates", use_container_width=True):
            before = st.session_state["df"]
            after = drop_duplicates_rows(before, subset=subset_cols, keep=keep)
            st.session_state["df"] = after
            refresh_profile()
            st.success(str(summarize_cleaning(before, after)))

st.divider()

# -------------------------
# Recompute button
# -------------------------
if st.button("Recompute profile"):
    refresh_profile()
    st.rerun()
