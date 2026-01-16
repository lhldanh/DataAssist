from __future__ import annotations

import os
import streamlit as st

st.title("Report")

st.session_state.setdefault("charts", [])
st.session_state.setdefault("report_sections", [])
st.session_state.setdefault("report_md", "")

df = st.session_state.get("df")
if df is None:
    st.warning("Please upload a dataset first.")
    st.stop()

# -------------------------
# Helpers
# -------------------------
def append_section(title: str, content):
    st.session_state.setdefault("report_sections", [])
    st.session_state["report_sections"].append({"title": title, "content": content})


def rebuild_report_md() -> str:
    """
    Build a Markdown export string from report_sections.
    Preview rendering is done separately (so we can use st.image reliably).
    """
    sections = st.session_state.get("report_sections") or []
    md = ""

    for s in sections:
        title = s.get("title", "Section")
        content = s.get("content", "")

        md += f"\n\n## {title}\n\n"

        # charts list section
        if isinstance(content, dict) and content.get("type") == "charts":
            for p in content.get("paths", []):
                md += f"![chart]({p})\n\n"
            continue

        # chart card section (single chart + optional llm)
        if isinstance(content, dict) and content.get("type") == "chart_card":
            p = content.get("path", "")
            if p:
                md += f"![chart]({p})\n\n"
            llm_md = content.get("llm_md")
            if llm_md:
                md += "### LLM write-up\n\n"
                md += f"{llm_md}\n"
            continue

        # normal text section
        md += f"{content}\n"

    st.session_state["report_md"] = md
    return md


# -------------------------
# Report preview (render from sections)
# -------------------------
st.subheader("Report preview")
sections = st.session_state.get("report_sections") or []

if not sections:
    st.info("Report is empty. Add sections from above.")
else:
    for s in sections:
        st.markdown(f"## {s.get('title', 'Section')}")
        content = s.get("content", "")

        # charts list
        if isinstance(content, dict) and content.get("type") == "charts":
            paths = content.get("paths", [])
            if not paths:
                st.info("No charts.")
            else:
                for p in paths:
                    if os.path.exists(p):
                        st.image(p, caption=os.path.basename(p))
                    else:
                        st.warning(f"Missing file: {p}")
            continue

        # chart card
        if isinstance(content, dict) and content.get("type") == "chart_card":
            p = content.get("path")
            if p and os.path.exists(p):
                st.image(p, caption=os.path.basename(p))
            else:
                st.warning(f"Missing file: {p}")

            llm_md = content.get("llm_md")
            if llm_md:
                st.markdown("### LLM write-up")
                st.markdown(llm_md)
            continue

        # normal markdown
        st.markdown(content)

st.divider()

# -------------------------
# Export
# -------------------------
st.subheader("Export")
md_for_export = rebuild_report_md() or ""

st.download_button(
    "⬇️ Download Markdown",
    data=md_for_export,
    file_name="report.md",
    mime="text/markdown",
    use_container_width=True
)

st.caption("PDF export can be added later (Markdown → HTML → PDF).")

st.divider()

# -------------------------
# Reset
# -------------------------
if st.button("🧹 Clear report"):
    st.session_state["report_sections"] = []
    rebuild_report_md()
    st.success("Report cleared.")
    st.rerun()
