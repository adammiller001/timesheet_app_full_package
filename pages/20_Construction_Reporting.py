import streamlit as st
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
        primary_label = str(sheet_df.columns[0]).strip() if len(sheet_df.columns) > 0 else "Selection"
        column_key = sheet_df.columns[0] if len(sheet_df.columns) > 0 else None

        if column_key is None or not primary_label:
            st.warning("Unable to determine dropdown label from cell A1.")
        else:
            values = []
            for raw_value in sheet_df[column_key].tolist():
                value = str(raw_value).strip()
                if value and value.lower() not in {"nan", "none"}:
                    values.append(value)

            seen = set()
            ordered_values = []
            for value in values:
                if value not in seen:
                    ordered_values.append(value)
                    seen.add(value)

            if not ordered_values:
                st.info("No options available for this category yet.")
            else:
                placeholder = f"Select {primary_label}..."
                detail_options = [placeholder] + ordered_values
                detail_key = f"construction_reporting_{category.lower().replace(' ', '_')}_detail"
                detail_choice = st.selectbox(
                    primary_label,
                    detail_options,
                    index=0,
                    key=detail_key,
                    help=f"Choose a {primary_label} to explore further.",
                )

                if detail_choice == placeholder:
                    st.info(f"Choose a {primary_label} to continue.")
                else:
                    st.info(f"'{detail_choice}' details coming soon.")
