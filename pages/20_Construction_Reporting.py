import streamlit as st
import pandas as pd

from app.integrations.google_sheets import read_timesheet_data

PAGE_TITLE = "Construction Reporting"
PAGE_ICON = "📊"

st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")
st.session_state["page_title"] = PAGE_TITLE
st.session_state["page_header"] = f"{PAGE_ICON} {PAGE_TITLE}"

# Gate: require login and admin access
if not st.session_state.get("authenticated", False):
    st.warning("Please sign in on the Home page first.")
    st.stop()

user_type = st.session_state.get("user_type", "User")
if user_type.upper() != "ADMIN":
    st.error("Access denied: Admin access required for this page.")
    st.info("This page is only available to administrators.")
    st.stop()

user = st.session_state.get("user_email")
st.sidebar.info(f"Signed in as: {user}")

st.title(st.session_state.get("page_header", "Page"))

CATEGORY_OPTIONS = [
    "Cable",
    "Glands",
    "Terminations",
    "Tray",
    "Equipment",
    "Junction Boxes",
    "Instruments",
    "Tubing",
]

select_options = ["Select a category..."] + CATEGORY_OPTIONS

category = st.selectbox(
    "Category",
    select_options,
    index=0,
    key="construction_reporting_category_v2",
    help="Choose the type of construction report to view.",
)

if category == select_options[0]:
    st.info("Select a category to start exploring construction reporting views.")
else:
    sheet_df = read_timesheet_data(category, force_refresh=True)

    if sheet_df.empty:
        st.warning("No data found for this category in Google Sheets.")
    else:
        sheet_df = sheet_df.copy()
        sheet_df.columns = [str(col).strip() for col in sheet_df.columns]

        chosen_label = None
        ordered_values = []

        for column in sheet_df.columns:
            series = sheet_df[column]
            cleaned = []
            for raw_value in series.tolist():
                if pd.isna(raw_value):
                    continue
                value = str(raw_value).strip()
                if value and value.lower() not in {"nan", "none"}:
                    cleaned.append(value)

            if cleaned:
                seen = set()
                deduped = []
                for item in cleaned:
                    if item not in seen:
                        deduped.append(item)
                        seen.add(item)
                if deduped:
                    chosen_label = str(column).strip() or "Selection"
                    ordered_values = deduped
                    break

        if not ordered_values or not chosen_label:
            st.info("No options available for this category yet.")
        else:
            placeholder = f"Select {chosen_label}..."
            detail_options = [placeholder] + ordered_values
            label_slug = ''.join(ch.lower() if ch.isalnum() else '_' for ch in chosen_label).strip('_') or 'field'
            detail_key = f"construction_reporting_{category.lower().replace(' ', '_')}_{label_slug}_detail"
            detail_choice = st.selectbox(
                chosen_label,
                detail_options,
                index=0,
                key=detail_key,
                help=f"Choose a {chosen_label} to explore further.",
            )

            if detail_choice == placeholder:
                st.info(f"Choose a {chosen_label} to continue.")
            else:
                st.info(f"'{detail_choice}' details coming soon.")
