from __future__ import annotations

import sys
from pathlib import Path

import atexit
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .../DataAssist
sys.path.insert(0, str(ROOT))

import streamlit as st
from core.loader import load_dataframe

APP_TITLE = "DataAssist"
APP_ICON = "📊"


def init_session_state() -> None:
    """Initialize keys used across pages."""
    defaults = {
        "df": None,
        "meta": None,          # loader metadata (file type, sheet names, etc.)
        "profile": None,       # cached EDA profile
        "insights": None,      # cached LLM insights
        "report_md": None,     # cached report markdown
        "charts": [],          # list of saved chart paths (optional)
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_workspace() -> None:
    """Hard reset current workspace (keeps app running)."""
    for k in ["df", "meta", "profile", "insights", "report_md", "charts"]:
        if k in st.session_state:
            st.session_state[k] = None if k != "charts" else []


def render_sidebar() -> None:
    with st.sidebar:
        st.title(f"{APP_ICON} {APP_TITLE}")
        st.caption("No-code data analysis with execution-based EDA + LLM-assisted writing.")

        st.divider()

        # Dataset status
        df = st.session_state.get("df")
        meta = st.session_state.get("meta") or {}

        if df is None:
            st.info("No dataset loaded yet.\n\nGo to **Upload** page to import a CSV/XLSX file.")
        else:
            rows, cols = df.shape
            st.success("Dataset loaded")
            st.write(f"- Rows: **{rows:,}**")
            st.write(f"- Columns: **{cols:,}**")

            if meta.get("file_type"):
                st.write(f"- Type: `{meta['file_type']}`")
            if meta.get("sheet"):
                st.write(f"- Sheet: `{meta['sheet']}`")

        st.divider()

        # Global actions
        if st.button("Reset workspace", use_container_width=True):
            reset_workspace()
            st.rerun()

        st.divider()

        st.caption(
            "Workflow: **Upload → Profile (EDA) → Visualize → Insights → Report**\n\n"
            "All statistics are computed by code; the LLM only helps write insights/reports."
        )


def landing_page() -> None:
    st.header(f"{APP_ICON} {APP_TITLE}")
    st.write(
        "A no-code data analysis assistant for **CSV/XLSX**.\n\n"
        "Use the pages on the left to run **execution-based EDA** and generate "
        "**LLM-assisted insights & reports** grounded in computed results."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Step 1", "Upload")
    c2.metric("Step 2", "Profile + Visualize")
    c3.metric("Step 3", "Insights + Report")

    st.divider()

    st.subheader("Quick start")
    st.write(
        "1) Open **Upload** page and import a dataset.\n"
        "2) Review missing values and basic stats in **Profile**.\n"
        "3) Create charts in **Visualize**.\n"
        "4) Generate written insights in **Insights**.\n"
        "5) Export a Markdown/PDF report in **Report**."
    )



def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_session_state()
    render_sidebar()

    # This main page is a landing page.
    # Streamlit will auto-discover multi-page scripts under app/pages/.
    landing_page()
    st.divider()
    st.subheader("📤 Upload dataset")

    file = st.file_uploader("Upload CSV/XLSX", type=["csv", "xlsx", "xls"])

    if file is not None:
        try:
            df, meta = load_dataframe(file)
        except Exception as e:
            st.error(f"Failed to load file: {e}")
            return

        st.session_state["df"] = df
        st.session_state["meta"] = meta

        # Reset cached outputs because dataset changed
        st.session_state["profile"] = None
        st.session_state["insights"] = None
        st.session_state["report_md"] = None
        st.session_state["charts"] = []

        st.success("Dataset loaded successfully.")
        st.dataframe(df.head(20), use_container_width=True)

def cleanup_on_exit():
    charts_dir = Path("artifacts/charts")
    if charts_dir.exists():
        shutil.rmtree(charts_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
    atexit.register(cleanup_on_exit)
