"""Initial application home view."""

import streamlit as st

from config.settings import get_settings

from app.ui.library import render_library


def render_home() -> None:
    """Render the course and lecture library."""
    st.set_page_config(
        page_title="Lecture Study Assistant",
        layout="centered",
    )
    st.title("Lecture Study Assistant")
    st.write(
        "A local-first workspace for turning university lecture materials "
        "into exam-oriented study guides."
    )
    render_library(get_settings())
