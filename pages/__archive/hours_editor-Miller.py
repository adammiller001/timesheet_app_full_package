from __future__ import annotations
import pandas as pd
import streamlit as st

def _render_editor(df: pd.DataFrame) -> pd.DataFrame:
    """
    Use st.data_editor if available; otherwise fall back to st.experimental_data_editor.
    If neither exists (very old Streamlit), show a minimal manual editor.
    """
    # Preferred (Streamlit â‰¥ 1.22)
    if hasattr(st, "data_editor"):
        try:
            return st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                key="hours_editor",
                column_config={
                    "Employee": st.column_config.TextColumn(required=True),
                    "RT Hours": st.column_config.NumberColumn(step=0.25, min_value=0.0),
                    "OT Hours": st.column_config.NumberColumn(step=0.25, min_value=0.0),
                    "Notes": st.column_config.TextColumn(),
                },
            )
        except Exception:
            # Some older sub-versions may not support column_config; try without it
            return st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                key="hours_editor_fallback",
            )

    # Older (pre-1.22)
    if hasattr(st, "experimental_data_editor"):
        return st.experimental_data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            key="hours_editor_exp",
        )

    # Very old fallback: render a simple form-like view
    st.info("Your Streamlit version is too old for the editor. Showing a basic fallback.")
    rows = []
    for i in range(len(df) or 1):
        c1, c2, c3, c4 = st.columns([3, 1, 1, 3])
        emp = c1.text_input(f"Employee {i+1}", df["Employee"][i] if i < len(df) else "")
        rt = c2.number_input(f"RT Hours {i+1}", min_value=0.0, step=0.25, value=float(df["RT Hours"][i]) if i < len(df) and df["RT Hours"][i] != "" else 0.0)
        ot = c3.number_input(f"OT Hours {i+1}", min_value=0.0, step=0.25, value=float(df["OT Hours"][i]) if i < len(df) and df["OT Hours"][i] != "" else 0.0)
        notes = c4.text_input(f"Notes {i+1}", df["Notes"][i] if i < len(df) else "")
        if emp:
            rows.append({"Employee": emp, "RT Hours": rt, "OT Hours": ot, "Notes": notes})
    return pd.DataFrame(rows, columns=["Employee", "RT Hours", "OT Hours", "Notes"])

def hours_editor(employee_list: list[str]) -> pd.DataFrame:
    """Render an hours editor seeded with selected employees and return the frame."""
    st.subheader("Enter Hours")
    if employee_list:
        seed_rows = pd.DataFrame(
            {
                "Employee": employee_list,
                "RT Hours": [0.0] * len(employee_list),
                "OT Hours": [0.0] * len(employee_list),
                "Notes": ["" for _ in employee_list],
            }
        )
    else:
        seed_rows = pd.DataFrame(columns=["Employee", "RT Hours", "OT Hours", "Notes"])

    return _render_editor(seed_rows)
