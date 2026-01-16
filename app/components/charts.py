from __future__ import annotations
import os
import time
import io
import streamlit as st

def fig_to_png_bytes(fig, dpi: int = 120) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    buf.seek(0)
    return buf.getvalue()

def show_fig_centered(fig, width: int = 520, dpi: int = 120):
    """Render centered chart at fixed pixel width (no saving)."""
    png = fig_to_png_bytes(fig, dpi=dpi)
    left, center, right = st.columns([1, 1, 1])
    with center:
        st.image(png, width=width)
    return png  # return bytes for optional save/analyze

def save_png_bytes(png: bytes, save_dir: str, filename_prefix: str = "chart") -> str:
    os.makedirs(save_dir, exist_ok=True)
    ts = int(time.time())
    path = os.path.join(save_dir, f"{filename_prefix}_{ts}.png")
    with open(path, "wb") as f:
        f.write(png)
    return path
