import streamlit as st
import pandas as pd
from datetime import date as date_cls
from typing import List, Tuple
from urllib.parse import quote

from app.integrations.google_sheets import get_sheets_manager, read_timesheet_data

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

if st.sidebar.button("Refresh All Dropdowns", use_container_width=True):
    st.session_state['force_fresh_data'] = True

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


def _get_column_a_details(sheet_name: str) -> Tuple[str, List[str]]:
    sheet_id = str(st.secrets.get("google_sheets_id", "")).strip()
    if not sheet_id:
        return "", []

    manager = get_sheets_manager()
    try:
        worksheet, actual_name = manager.find_worksheet([sheet_name], sheet_id)
    except Exception:
        return "", []

    actual_title = actual_name or sheet_name
    header = ""
    values: List[str] = []

    def _clean_and_dedupe(raw_values: List[str]) -> List[str]:
        cleaned: List[str] = []
        for raw in raw_values:
            value = str(raw).strip()
            if not value:
                continue
            lower = value.lower()
            if lower in {"nan", "none"}:
                continue
            cleaned.append(value)
        seen: set[str] = set()
        ordered: List[str] = []
        for item in cleaned:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered

    if worksheet is not None and hasattr(worksheet, "col_values"):
        try:
            column_values = worksheet.col_values(1)
        except Exception:
            column_values = []
        else:
            if column_values:
                header = str(column_values[0]).strip()
                if len(column_values) > 1:
                    values = _clean_and_dedupe(column_values[1:])
                if header or values:
                    return header, values

    session = manager._ensure_session()
    if session is None:
        return header, values

    try:
        quoted_title = quote(actual_title)
        range_ref = f"{quoted_title}!A:A"
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_ref}"
        params = {"valueRenderOption": "UNFORMATTED_VALUE", "dateTimeRenderOption": "FORMATTED_STRING"}
        response = session.get(url, params=params)
        response.raise_for_status()
        values_data = response.json().get("values", [])
    except Exception:
        return header, values

    if not values_data:
        return header, values

    first_row = values_data[0] if values_data else []
    if first_row:
        header = str(first_row[0]).strip()

    column_entries: List[str] = []
    for row in values_data[1:]:
        if not row:
            continue
        column_entries.append(row[0])

    values = _clean_and_dedupe(column_entries)
    return header, values


def _update_cable_row(sheet_name: str, tag_value: str, updates: dict[str, object]) -> bool:
    sheet_id = str(st.secrets.get("google_sheets_id", "")).strip()
    if not sheet_id:
        st.error("Google Sheets ID is not configured.")
        return False

    manager = get_sheets_manager()
    try:
        worksheet, actual_name = manager.find_worksheet([sheet_name], sheet_id)
    except Exception as exc:
        st.error(f"Could not locate worksheet '{sheet_name}': {exc}")
        return False

    actual_title = actual_name or sheet_name
    try:
        df = manager.read_worksheet(actual_title, sheet_id, force_refresh=True)
    except Exception as exc:
        st.error(f"Failed to read worksheet '{actual_title}': {exc}")
        return False

    if df.empty or df.shape[1] == 0:
        st.error("Worksheet does not contain data to update.")
        return False

    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    tag_column = df.columns[0]
    match_mask = df[tag_column].astype(str).str.strip() == str(tag_value).strip()
    if not match_mask.any():
        st.error("Selected cable tag could not be found in the worksheet.")
        return False

    first_match_idx = df[match_mask].index[0]
    updated_row = df.loc[first_match_idx].copy()

    for col, value in updates.items():
        if col not in df.columns:
            continue
        if hasattr(value, "strftime"):
            updated_row[col] = value.strftime('%Y-%m-%d')
        else:
            updated_row[col] = value

    df.loc[first_match_idx] = updated_row

    try:
        return manager.write_worksheet(actual_title, df, sheet_id)
    except Exception as exc:
        st.error(f"Failed to write updates to worksheet '{actual_title}': {exc}")
        return False


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
    column_label, column_values = _get_column_a_details(category)

    primary_label = (column_label or "Selection").strip() or "Selection"
    placeholder = f"Select {primary_label}..."

    if not column_label and not column_values and sheet_df.empty:
        st.warning("No data found for this category in Google Sheets.")

    detail_options = [placeholder] + column_values if column_values else [placeholder]

    label_slug = ''.join(ch.lower() if ch.isalnum() else '_' for ch in primary_label).strip('_') or 'field'
    detail_key = f"construction_reporting_{category.lower().replace(' ', '_')}_{label_slug}_detail"
    detail_choice = st.selectbox(
        primary_label,
        detail_options,
        index=0,
        key=detail_key,
        help=f"Choose a {primary_label} to explore further.",
    )

    if detail_choice == placeholder:
        if column_values:
            st.info(f"Choose a {primary_label} to continue.")
        else:
            st.info(f"No {primary_label} values found in this sheet yet.")
    else:
        normalized_category = category.strip().lower()
        if normalized_category == "cable":
            if sheet_df.empty:
                st.warning("No cable data is available to display.")
            else:
                working_df = sheet_df.copy()
                working_df.columns = [str(col).strip() for col in working_df.columns]
                if not list(working_df.columns):
                    st.warning("Cable sheet is missing header information.")
                else:
                    tag_column = working_df.columns[0]
                    matched_rows = working_df[working_df[tag_column].astype(str).str.strip() == detail_choice.strip()]
                    if matched_rows.empty:
                        st.warning("Unable to locate details for the selected cable tag.")
                    else:
                        row = matched_rows.iloc[0]
                        detail_columns = working_df.columns[1:11]
                        if not list(detail_columns):
                            st.info("No additional columns (B-K) are available for this cable sheet.")
                        else:
                            detail_records = []
                            for col in detail_columns:
                                raw_value = row.get(col, "")
                                value = "" if pd.isna(raw_value) else str(raw_value).strip()
                                detail_records.append({"Field": col, "Value": value})
                            details_df = pd.DataFrame(detail_records)
                            st.subheader("Cable Details")
                            st.table(details_df)

                            mirror_columns = working_df.columns[11:14]
                            mirror_data = []
                            for col in mirror_columns:
                                raw_value = row.get(col, "")
                                if pd.isna(raw_value):
                                    value = ""
                                elif col and 'date' in col.lower():
                                    parsed = pd.to_datetime(raw_value, errors='coerce')
                                    value = parsed.strftime('%Y-%m-%d') if pd.notna(parsed) else str(raw_value).strip()
                                else:
                                    value = str(raw_value).strip()
                                mirror_data.append((col, value))

                            st.write("")
                            st.subheader("Update Cable Status")
                            updated_values = {}
                            tag_slug = ''.join(ch.lower() if ch.isalnum() else '_' for ch in detail_choice).strip('_') or 'tag'
                            for col, current_value in mirror_data:
                                label = col if col else "Field"
                                input_key = f"cable_update_{tag_slug}_{''.join(ch.lower() if ch.isalnum() else '_' for ch in (col or 'field')).strip('_')}"
                                if label.lower() == 'date pulled':
                                    default_date = None
                                    if current_value:
                                        parsed_date = pd.to_datetime(current_value, errors='coerce')
                                        if pd.notna(parsed_date):
                                            default_date = parsed_date.date()
                                    date_col, clear_col = st.columns([3, 1])
                                    with date_col:
                                        date_value = st.date_input(
                                            label,
                                            value=default_date or date_cls.today(),
                                            key=input_key,
                                            format="YYYY-MM-DD"
                                        )
                                    clear_key = f"{input_key}_clear"
                                    with clear_col:
                                        clear_selected = st.checkbox(
                                            "Clear",
                                            value=default_date is None,
                                            key=clear_key,
                                            help="Tick to leave the date blank."
                                        )
                                    updated_values[col] = "" if clear_selected else date_value
                                else:
                                    updated_values[col] = st.text_input(
                                        label,
                                        value=current_value,
                                        key=input_key
                                    )

                            if st.button("Submit", type="primary"):
                                try:
                                    updates_to_apply = {}
                                    for col, value in updated_values.items():
                                        if isinstance(value, pd.Timestamp):
                                            updates_to_apply[col] = value.strftime('%Y-%m-%d')
                                        elif hasattr(value, 'strftime') and not isinstance(value, str):
                                            updates_to_apply[col] = value.strftime('%Y-%m-%d')
                                        else:
                                            updates_to_apply[col] = value

                                    if not updates_to_apply:
                                        st.warning("Nothing to update for this cable tag.")
                                    else:
                                        if _update_cable_row(category, detail_choice.strip(), updates_to_apply):
                                            st.success("Cable details updated successfully.")
                                            st.experimental_rerun()
                                        else:
                                            st.error("Failed to update cable details.")
                                except Exception as exc:
                                    st.error(f"Unexpected error while submitting updates: {exc}")
        else:
            st.info(f"'{detail_choice}' details coming soon.")
