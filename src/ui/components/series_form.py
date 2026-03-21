"""Shared add/edit form shell used by all series type pages."""

from __future__ import annotations

from typing import Callable

import streamlit as st


def series_form_shell(
    title: str,
    form_key: str,
    content_fn: Callable[[], dict | None],
    on_confirm: Callable[[dict], None],
    on_cancel: Callable[[], None] | None = None,
) -> None:
    """Render a consistent add/edit form shell for all series types.

    Displays a header, calls content_fn to render form body,
    and shows confirm/cancel buttons at the bottom.

    Args:
        title: Section header text.
        form_key: Unique key for the Streamlit form widget.
        content_fn: Callable that renders the form fields and returns a dict
                    of field values, or None if validation fails.
        on_confirm: Callback invoked with the field-value dict on confirmation.
        on_cancel: Optional callback invoked when the cancel button is clicked.
    """
    st.subheader(title)
    with st.form(key=form_key):
        result = content_fn()
        col1, col2 = st.columns([1, 1])
        with col1:
            confirmed = st.form_submit_button("Hinzufügen")
        with col2:
            cancelled = st.form_submit_button("Abbrechen")

    if confirmed and result is not None:
        on_confirm(result)
    if cancelled and on_cancel is not None:
        on_cancel()
