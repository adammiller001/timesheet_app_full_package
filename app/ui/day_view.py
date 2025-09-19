import datetime as dt
import pandas as pd
import streamlit as st
from app.data.workbook import get_time_data

def day_view():
    xlsx_path = st.session_state.xlsx_path
    date_val = st.session_state.get("current_date") or dt.date.today()
    td = get_time_data(xlsx_path)
    if td.empty:
        st.caption("empty"); return
    td["DateStr"] = td["Date"].astype(str).str[:10]
    mask = td["DateStr"] == date_val.strftime("%Y-%m-%d")
    day_df = td[mask].copy()
    if day_df.empty:
        st.caption("empty"); return
    show_cols = ["Job Number","Job Area","Date","Name","Class Type","Trade Class","Employee Number","RT Hours","OT Hours","Comments"]
    show_cols = [c for c in show_cols if c in day_df.columns]
    display_df = day_df.reset_index(drop=True).copy()
    display_df.insert(0, "IDX", display_df.index)
    st.dataframe(display_df[["IDX"] + show_cols], use_container_width=True, hide_index=True)
