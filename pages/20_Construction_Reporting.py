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
    "EHT",
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



def _column_letter(col_index: int) -> str:
    if col_index <= 0:
        raise ValueError("Column index must be positive")
    result = []
    current = col_index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        result.append(chr(65 + remainder))
    return ''.join(reversed(result))


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
    columns = df.columns.tolist()
    tag_column = columns[0]
    match_mask = df[tag_column].astype(str).str.strip() == str(tag_value).strip()
    if not match_mask.any():
        st.error("Selected cable tag could not be found in the worksheet.")
        return False

    first_match_idx = df[match_mask].index[0]
    row_number = first_match_idx + 2  # account for header row

    payload: list[tuple[int, str]] = []
    for col, value in updates.items():
        if col not in columns:
            continue
        col_idx = columns.index(col) + 1
        if value is None:
            str_value = ''
        elif hasattr(value, 'strftime') and not isinstance(value, str):
            str_value = value.strftime('%Y-%m-%d')
        else:
            str_value = str(value).strip()
        payload.append((col_idx, str_value))
        df.at[first_match_idx, col] = str_value

    if not payload:
        return True

    if worksheet is not None and hasattr(worksheet, 'update'):
        try:
            for col_idx, str_value in payload:
                worksheet.update_cell(row_number, col_idx, str_value)
            if hasattr(manager, '_data_cache'):
                manager._data_cache.pop(actual_title, None)
            return True
        except Exception as exc:
            st.warning(f"Direct cell update failed: {exc}. Falling back to full-sheet write.")

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

    normalized_category = category.strip().lower()
    primary_label = (column_label or "Selection").strip() or "Selection"
    placeholder = f"Select {primary_label}..."

    only_incomplete_flag = False
    toggle_key = None
    if normalized_category == "cable":
        toggle_key = "cable_only_incomplete_toggle"
        only_incomplete_flag = st.checkbox(
            "Only Show Incomplete Cables",
            value=st.session_state.get(toggle_key, False),
            key=toggle_key,
            help="Filter to cables missing Date Pulled or Checked By."
        )
    elif normalized_category == "glands":
        toggle_key = "glands_only_incomplete_toggle"
        only_incomplete_flag = st.checkbox(
            "Only Show Incomplete Glands",
            value=st.session_state.get(toggle_key, False),
            key=toggle_key,
            help="Filter to glands missing status fields."
        )
    elif normalized_category == "terminations":
        toggle_key = "terminations_only_incomplete_toggle"
        only_incomplete_flag = st.checkbox(
            "Only Show Incomplete Terminations",
            value=st.session_state.get(toggle_key, False),
            key=toggle_key,
            help="Filter to terminations missing completion dates."
        )

    if normalized_category in ("cable", "glands", "terminations") and not sheet_df.empty:
        working_df_options = sheet_df.copy()
        working_df_options.columns = [str(col).strip() for col in working_df_options.columns]
        if working_df_options.columns.tolist():
            tag_column = working_df_options.columns[0]
            if normalized_category == "cable":
                status_cols = list(working_df_options.columns[12:15])
            elif normalized_category == "glands":
                status_cols = list(working_df_options.columns[5:10])
            else:
                status_cols = list(working_df_options.columns[7:9])
            filtered_tags = []
            seen_tags = set()
            for _, entry_row in working_df_options.iterrows():
                tag_value = str(entry_row.get(tag_column, "")).strip()
                if not tag_value:
                    continue
                if only_incomplete_flag:
                    completeness = [str(entry_row.get(col, "")).strip() for col in status_cols]
                    if status_cols and all(completeness):
                        continue
                if tag_value not in seen_tags:
                    seen_tags.add(tag_value)
                    filtered_tags.append(tag_value)
            column_values = filtered_tags

    if normalized_category == "cable" and not sheet_df.empty:
        working_df_options = sheet_df.copy()
        working_df_options.columns = [str(col).strip() for col in working_df_options.columns]
        if working_df_options.columns.tolist():
            tag_column = working_df_options.columns[0]
            status_cols = list(working_df_options.columns[12:15])
            filtered_tags = []
            seen_tags = set()
            for _, cable_row in working_df_options.iterrows():
                tag_value = str(cable_row.get(tag_column, "")).strip()
                if not tag_value:
                    continue
                if only_incomplete_flag:
                    completeness = [str(cable_row.get(col, "")).strip() for col in status_cols]
                    if status_cols and all(completeness):
                        continue
                if tag_value not in seen_tags:
                    seen_tags.add(tag_value)
                    filtered_tags.append(tag_value)
            column_values = filtered_tags

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
                        detail_columns = working_df.columns[1:12]
                        if not list(detail_columns):
                            st.info("No additional columns (B-L) are available for this cable sheet.")
                        else:
                            detail_records = []
                            for col in detail_columns:
                                raw_value = row.get(col, "")
                                value = "" if pd.isna(raw_value) else str(raw_value).strip()
                                detail_records.append({"Field": col, "Value": value})
                            details_df = pd.DataFrame(detail_records)
                            st.subheader("Cable Details")
                            st.table(details_df)

                            mirror_columns = list(working_df.columns[12:15])
                            mirror_data = []
                            pulled_status_column = mirror_columns[0] if mirror_columns else None
                            pulled_signoff_column = working_df.columns[15] if len(working_df.columns) > 15 else None
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
                                    date_value = st.date_input(
                                        label,
                                        value=default_date or date_cls.today(),
                                        key=input_key,
                                        format="YYYY-MM-DD"
                                    )
                                    updated_values[col] = date_value
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

                                    if updates_to_apply and pulled_status_column and pulled_signoff_column:
                                        user_identifier = (
                                            st.session_state.get("user_name")
                                            or st.session_state.get("user_email")
                                            or st.session_state.get("user")
                                            or "Unknown User"
                                        )
                                        if pulled_status_column in updates_to_apply:
                                            pulled_value = updates_to_apply[pulled_status_column]
                                            if pulled_value is None or (isinstance(pulled_value, str) and not pulled_value.strip()):
                                                updates_to_apply[pulled_signoff_column] = ""
                                            else:
                                                updates_to_apply[pulled_signoff_column] = user_identifier
                                    if not updates_to_apply:
                                        st.warning("Nothing to update for this cable tag.")
                                    else:
                                        if _update_cable_row(category, detail_choice.strip(), updates_to_apply):
                                            st.success("Cable details updated successfully.")
                                            st.rerun()
                                        else:
                                            st.error("Failed to update cable details.")
                                except Exception as exc:
                                    st.error(f"Unexpected error while submitting updates: {exc}")
        elif normalized_category == "terminations":
            if sheet_df.empty:
                st.warning("No termination data is available to display.")
            else:
                working_df = sheet_df.copy()
                working_df.columns = [str(col).strip() for col in working_df.columns]
                if not list(working_df.columns):
                    st.warning("Terminations sheet is missing header information.")
                else:
                    tag_column = working_df.columns[0]
                    matched_rows = working_df[working_df[tag_column].astype(str).str.strip() == detail_choice.strip()]
                    if matched_rows.empty:
                        st.warning("Unable to locate details for the selected termination tag.")
                    else:
                        row = matched_rows.iloc[0]
                        detail_columns = working_df.columns[1:7]
                        if not list(detail_columns):
                            st.info("No additional columns (B-G) are available for this terminations sheet.")
                        else:
                            detail_records = []
                            for col in detail_columns:
                                raw_value = row.get(col, "")
                                value = "" if pd.isna(raw_value) else str(raw_value).strip()
                                detail_records.append({"Field": col, "Value": value})
                            details_df = pd.DataFrame(detail_records)
                            st.subheader("Termination Details")
                            st.table(details_df)

                        status_columns = list(working_df.columns[7:10])
                        signoff_columns = {}
                        if len(working_df.columns) > 10 and len(status_columns) > 0:
                            signoff_columns[status_columns[0]] = working_df.columns[10]
                        if len(working_df.columns) > 11 and len(status_columns) > 1:
                            signoff_columns[status_columns[1]] = working_df.columns[11]
                        if not list(status_columns):
                            st.info("No status columns (H-J) are available for this terminations sheet.")
                        else:
                            status_data = []
                            for col in status_columns:
                                raw_value = row.get(col, "")
                                if pd.isna(raw_value):
                                    value = ""
                                else:
                                    parsed_value = pd.to_datetime(raw_value, errors="coerce")
                                    if pd.notna(parsed_value):
                                        value = parsed_value.strftime("%Y-%m-%d")
                                    else:
                                        value = str(raw_value).strip()
                                status_data.append((col, value))

                            st.write("")
                            st.subheader("Update Termination Status")
                            updated_values = {}
                            tag_slug = ''.join(ch.lower() if ch.isalnum() else '_' for ch in detail_choice).strip('_') or 'tag'
                            for idx, (col, current_value) in enumerate(status_data):
                                label = col if col else "Field"
                                input_key = f"termination_update_{tag_slug}_{''.join(ch.lower() if ch.isalnum() else '_' for ch in (col or 'field')).strip('_')}"
                                if idx < 2:
                                    default_date = None
                                    if current_value:
                                        parsed_date = pd.to_datetime(current_value, errors="coerce")
                                        if pd.notna(parsed_date):
                                            default_date = parsed_date.date()
                                    date_value = st.date_input(
                                        label,
                                        value=default_date,
                                        key=input_key,
                                        format="YYYY-MM-DD"
                                    )
                                    updated_values[col] = date_value if date_value else None
                                else:
                                    updated_values[col] = st.text_input(
                                        label,
                                        value=current_value,
                                        key=input_key
                                    )

                            if st.button("Submit Termination Status", type="primary"):
                                try:
                                    updates_to_apply = {}
                                    for col, value in updated_values.items():
                                        if isinstance(value, pd.Timestamp):
                                            updates_to_apply[col] = value.strftime("%Y-%m-%d")
                                        elif hasattr(value, "strftime") and not isinstance(value, str):
                                            updates_to_apply[col] = value.strftime("%Y-%m-%d")
                                        else:
                                            updates_to_apply[col] = value

                                    if updates_to_apply:
                                        user_identifier = (
                                            st.session_state.get("user_name")
                                            or st.session_state.get("user_email")
                                            or st.session_state.get("user")
                                            or "Unknown User"
                                        )
                                        for col in status_columns[:2]:
                                            signoff_col = signoff_columns.get(col)
                                            if not signoff_col or col not in updates_to_apply:
                                                continue
                                            value = updates_to_apply[col]
                                            if value is None or (isinstance(value, str) and not value.strip()):
                                                updates_to_apply[signoff_col] = ""
                                            else:
                                                updates_to_apply[signoff_col] = user_identifier

                                    if not updates_to_apply:
                                        st.warning("Nothing to update for this termination tag.")
                                    else:
                                        if _update_cable_row(category, detail_choice.strip(), updates_to_apply):
                                            st.success("Termination details updated successfully.")
                                            st.rerun()
                                        else:
                                            st.error("Failed to update termination details.")
                                except Exception as exc:
                                    st.error(f"Unexpected error while submitting termination updates: {exc}")

        elif normalized_category == "glands":
            if sheet_df.empty:
                st.warning("No gland data is available to display.")
            else:
                working_df = sheet_df.copy()
                working_df.columns = [str(col).strip() for col in working_df.columns]
                if not list(working_df.columns):
                    st.warning("Glands sheet is missing header information.")
                else:
                    tag_column = working_df.columns[0]
                    matched_rows = working_df[working_df[tag_column].astype(str).str.strip() == detail_choice.strip()]
                    if matched_rows.empty:
                        st.warning("Unable to locate details for the selected gland tag.")
                    else:
                        row = matched_rows.iloc[0]
                        detail_columns = working_df.columns[1:5]
                        if not list(detail_columns):
                            st.info("No additional columns (B-E) are available for this glands sheet.")
                        else:
                            detail_records = []
                            for col in detail_columns:
                                raw_value = row.get(col, "")
                                value = "" if pd.isna(raw_value) else str(raw_value).strip()
                                detail_records.append({"Field": col, "Value": value})
                            details_df = pd.DataFrame(detail_records)
                            st.subheader("Gland Details")
                            st.table(details_df)
                            status_columns = working_df.columns[5:10]
                            source_status_column = status_columns[0] if status_columns else None
                            destination_status_column = status_columns[1] if len(status_columns) > 1 else None
                            source_signoff_column = working_df.columns[10] if len(working_df.columns) > 10 else None
                            destination_signoff_column = working_df.columns[11] if len(working_df.columns) > 11 else None
                            if not list(status_columns):
                                st.info("No status columns (F-J) are available for this glands sheet.")
                            else:
                                status_data = []
                                for col in status_columns:
                                    raw_value = row.get(col, "")
                                    if pd.isna(raw_value):
                                        value = ""
                                    elif col and 'date' in col.lower():
                                        parsed = pd.to_datetime(raw_value, errors='coerce')
                                        value = parsed.strftime('%Y-%m-%d') if pd.notna(parsed) else str(raw_value).strip()
                                    else:
                                        value = str(raw_value).strip()
                                    status_data.append((col, value))

                                st.write("")
                                st.subheader("Update Gland Status")
                                updated_values = {}
                                tag_slug = ''.join(ch.lower() if ch.isalnum() else '_' for ch in detail_choice).strip('_') or 'tag'
                                for col, current_value in status_data:
                                    label = col if col else "Field"
                                    input_key = f"gland_update_{tag_slug}_{''.join(ch.lower() if ch.isalnum() else '_' for ch in (col or 'field')).strip('_')}"
                                    if label and 'date' in label.lower():
                                        default_date = None
                                        if current_value:
                                            parsed_date = pd.to_datetime(current_value, errors='coerce')
                                            if pd.notna(parsed_date):
                                                default_date = parsed_date.date()
                                        date_value = st.date_input(
                                            label,
                                            value=default_date or date_cls.today(),
                                            key=input_key,
                                            format="YYYY-MM-DD"
                                        )
                                        updated_values[col] = date_value
                                    else:
                                        updated_values[col] = st.text_input(
                                            label,
                                            value=current_value,
                                            key=input_key
                                        )

                                if st.button("Submit Gland Status", type="primary"):
                                    try:
                                        updates_to_apply = {}
                                        for col, value in updated_values.items():
                                            if isinstance(value, pd.Timestamp):
                                                updates_to_apply[col] = value.strftime('%Y-%m-%d')
                                            elif hasattr(value, 'strftime') and not isinstance(value, str):
                                                updates_to_apply[col] = value.strftime('%Y-%m-%d')
                                            else:
                                                updates_to_apply[col] = value

                                        if updates_to_apply:
                                            user_identifier = (
                                                st.session_state.get("user_name")
                                                or st.session_state.get("user_email")
                                                or st.session_state.get("user")
                                                or "Unknown User"
                                            )
                                            if source_status_column and source_signoff_column and source_status_column in updates_to_apply:
                                                source_value = updates_to_apply[source_status_column]
                                                if source_value is None or (isinstance(source_value, str) and not source_value.strip()):
                                                    updates_to_apply[source_signoff_column] = ""
                                                else:
                                                    updates_to_apply[source_signoff_column] = user_identifier
                                            if destination_status_column and destination_signoff_column and destination_status_column in updates_to_apply:
                                                dest_value = updates_to_apply[destination_status_column]
                                                if dest_value is None or (isinstance(dest_value, str) and not dest_value.strip()):
                                                    updates_to_apply[destination_signoff_column] = ""
                                                else:
                                                    updates_to_apply[destination_signoff_column] = user_identifier
                                        if not updates_to_apply:
                                            st.warning("Nothing to update for this gland tag.")
                                        else:
                                            if _update_cable_row(category, detail_choice.strip(), updates_to_apply):
                                                st.success("Gland details updated successfully.")
                                                st.rerun()
                                            else:
                                                st.error("Failed to update gland details.")
                                    except Exception as exc:
                                        st.error(f"Unexpected error while submitting gland updates: {exc}")

        else:
            st.info(f"'{detail_choice}' details coming soon.")

