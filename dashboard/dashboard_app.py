"""
dashboard_app.py

WHY THIS FILE EXISTS:
This is the single entry point for the whole dashboard. Instead of
Streamlit's older "pages/" folder magic (which infers page order and
names from filenames), we use st.navigation() to explicitly define
every page, its title, and its icon -- more predictable and easier to
extend later.

RUN WITH: streamlit run dashboard_app.py
(Make sure the FastAPI backend is also running: uvicorn main:app --reload --port 8000)
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from views import overview, manual_entry, trends, history
from style import icon_html

st.set_page_config(
    page_title="GAIL Predictive Maintenance",
    page_icon="🛢️",
    layout="wide",
)

pages = [
    st.Page(overview.render, title="Overview", icon=":material/dashboard:", url_path="overview", default=True),
    st.Page(manual_entry.render, title="Manual Entry", icon=":material/edit_note:", url_path="manual-entry"),
    st.Page(trends.render, title="Trends", icon=":material/show_chart:", url_path="trends"),
    st.Page(history.render, title="History", icon=":material/history:", url_path="history"),
]

nav = st.navigation(pages)

with st.sidebar:
    st.markdown(
        f"<div style='font-weight:700; font-size:1.05rem; margin-bottom:2px;'>"
        f"{icon_html('factory', 20)} GAIL Predictive Maintenance</div>"
        "<div style='font-size:0.78rem; opacity:0.8; margin-bottom:18px;'>"
        "Compressor fleet monitoring prototype</div>",
        unsafe_allow_html=True,
    )

nav.run()
