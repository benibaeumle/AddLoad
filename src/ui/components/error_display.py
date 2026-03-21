"""Error display component: renders inline German error messages."""

from __future__ import annotations

import streamlit as st


def show_errors(errors: list[str]) -> None:
    """Render a list of German error messages inline via st.error.

    Args:
        errors: List of German error message strings to display.
                Stack traces are never shown (UX-002).
    """
    for msg in errors:
        st.error(msg)
