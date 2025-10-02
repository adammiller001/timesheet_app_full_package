import streamlit as st
import pandas as pd
import time
from pathlib import Path
import tempfile
import shutil

from app.style_utils import apply_watermark
from app.config import get_default_xlsx_path

try:
    from app.integrations.google_sheets import read_timesheet_data, get_sheets_manager
    HAVE_GOOGLE_SHEETS = True
except Exception:
    HAVE_GOOGLE_SHEETS = False
    read_timesheet_data = None
    get_sheets_manager = None

# Configure page
st.set_page_config(
    page_title="PTW - Daily Timesheet Suite",
    page_icon="?",
    layout="wide"
)

apply_watermark()


def load_users(force_refresh=False):
    """Load users from Google Sheets when available, otherwise fall back to the local workbook."""
    google_error = None
    sheet_id = st.secrets.get("google_sheets_id", "")
    if HAVE_GOOGLE_SHEETS and read_timesheet_data and sheet_id:
        manager = get_sheets_manager()
        if force_refresh:
            if hasattr(manager, "_data_cache"):
                manager._data_cache.pop("Users", None)  # type: ignore[attr-defined]
            if hasattr(manager, "spreadsheet"):
                manager.spreadsheet = None
        worksheet, actual_title = manager.find_worksheet(["Users", "User"], sheet_id)
        if actual_title:
            try:
                users_df = manager.read_worksheet(actual_title, sheet_id, force_refresh=force_refresh)
                if not users_df.empty:
                    users_df = users_df.copy()
                    users_df.columns = [str(col).strip() for col in users_df.columns]
                    return users_df, None
                google_error = f"Google Sheets worksheet '{actual_title}' is empty."
            except Exception as exc:
                google_error = f"Google Sheets error: {exc}"
        else:
            google_error = "Users worksheet not found in Google Sheets."
    else:
        google_error = "Google Sheets integration is not configured."

    # Local Excel fallback
    workbook_path = get_default_xlsx_path()
    local_error = None
    if workbook_path:
        file_path = Path(workbook_path)
        if file_path.exists():
            try:
                excel = pd.ExcelFile(file_path)
                def _match(target: str) -> str | None:
                    target_norm = target.strip().lower()
                    for sheet in excel.sheet_names:
                        if sheet.strip().lower() == target_norm:
                            return sheet
                    return None
                for candidate in ("Users", "User"):
                    sheet_name = _match(candidate)
                    if not sheet_name:
                        continue
                    df = safe_read_excel(file_path, sheet_name, force_refresh=force_refresh)
                    if not df.empty:
                        df = df.copy()
                        df.columns = [str(col).strip() for col in df.columns]
                        return df, None
                local_error = "Users worksheet not found in local workbook."
            except Exception as exc:
                local_error = f"Unable to read Excel workbook: {exc}"
        else:
            local_error = f"Excel file not found at {file_path}"
    return pd.DataFrame(), local_error or google_error or local_error
    return pd.DataFrame(), google_error

def authenticate_user(email, force_refresh=False):
    """Check if user email exists in Users worksheet and return user type"""
    users_df, error = load_users(force_refresh=force_refresh)
    if error:
        message = str(error)
        if "not configured" in message.lower():
            st.warning("Google Sheets integration is not configured; granting temporary admin access.")
            return True, "Admin", None
        return False, "User", error

    if users_df.empty:
        return False, "User", "No users found in worksheet"

    # Look for email in various possible column names
    email_columns = ["Email", "User Email", "Email Address", "Login Email", "User's Email Address"]
    normalized_columns = {str(col).strip().lower(): col for col in users_df.columns}
    email_col = None

    for col in email_columns:
        actual_col = normalized_columns.get(col.strip().lower())
        if actual_col:
            email_col = actual_col
            break

    if not email_col:
        return False, "User", f"Email column not found. Available columns: {list(users_df.columns)}"

    # Check if email exists
    user_row = users_df[users_df[email_col].astype(str).str.lower() == email.lower()]
    if user_row.empty:
        return False, "User", "Email not found in users list"

    # Check user type (Admin or User)
    type_candidates = ["User Type", "UserType", "Role", "Access Level", "Type"]
    raw_user_type = "User"  # Default
    for candidate in type_candidates:
        actual_col = normalized_columns.get(candidate.strip().lower())
        if actual_col and actual_col in users_df.columns:
            raw_user_type = users_df.loc[user_row.index, actual_col].iloc[0]
            break

    user_type_clean = str(raw_user_type).strip() if raw_user_type is not None else ""
    user_type_upper = user_type_clean.upper()

    if "ADMIN" in user_type_upper:
        normalized_type = "Admin"
    elif user_type_upper in {"USER", "STANDARD", "EMPLOYEE"}:
        normalized_type = "User"
    else:
        normalized_type = user_type_clean or "User"

    return True, normalized_type, None

# Force clear any potentially corrupt session state
if st.session_state.get("authenticated") and not st.session_state.get("user_email"):
    st.session_state["user_email"] = None
    st.session_state["user_type"] = None
    st.session_state["authenticated"] = False

# Check if user is logged in
if "user_email" not in st.session_state:
    st.session_state["user_email"] = None
    st.session_state["user_type"] = None
    st.session_state["authenticated"] = False


# Show login form if not authenticated
if not st.session_state.get("authenticated", False):
    st.title("🔐 PTW - Daily Timesheet Suite")
    st.markdown("### Please sign in with your work email")

    with st.form("login_form"):
        email = st.text_input("Email Address", placeholder="you@ptwenergy.com").strip().lower()
        submitted = st.form_submit_button("Sign In", type="primary")

        if submitted:
            if not email:
                st.error("Please enter your email address")
            else:
                # Force refresh authentication data on every login attempt
                is_valid, user_type, error = authenticate_user(email, force_refresh=True)
                if is_valid:
                    st.session_state["user_email"] = email
                    st.session_state["user_type"] = user_type
                    st.session_state["authenticated"] = True
                    st.success(f"Welcome! Signed in as {user_type}")
                    st.rerun()
                else:
                    st.error(f"Access denied: {error}")
                    st.info("Please contact your administrator if you believe this is an error")

else:
    # User is authenticated - show main app
    st.title("📊 PTW - Daily Timesheet Suite")

    # Show user info in sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"**👤 Signed in as:**")
        st.markdown(f"📧 {st.session_state['user_email']}")
        st.markdown(f"🏷️ {st.session_state['user_type']}")

        if st.button("🚪 Sign Out"):
            st.session_state["user_email"] = None
            st.session_state["user_type"] = None
            st.session_state["authenticated"] = False
            st.rerun()

        # Temporary debug button - remove after fixing
        if st.button("🔄 Clear Session (Debug)"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        st.markdown("---")

    # Welcome message
    user_type = st.session_state.get("user_type", "User")
    st.write(f"Welcome to the PTW Timesheet Management System, {user_type}!")


    # Navigation instructions based on user type
    st.markdown("---")
    st.markdown("### Available Pages")

    if user_type.upper() == "ADMIN":
        st.markdown("""
        **Use the sidebar to navigate to different features:**

        - **📝 Timesheet Entry** - Add and manage time entries
        - **📊 Construction Reporting** - View today's entries *(Admin Access)*
        - **📤 Export Day** - Generate Daily Time and Daily Import reports
        - **⚙️ Admin** - Administrative functions *(Admin Access)*

        ### Admin Features:
        - Full access to all features
        - View all time entries
        - Administrative functions
        """)
    else:
        st.markdown("""
        **Use the sidebar to navigate to different features:**

        - **📝 Timesheet Entry** - Add and manage time entries
        - **📤 Export Day** - Generate Daily Time and Daily Import reports

        ### User Features:
        - Add time entries for employees
        - Export Daily Time and Daily Import formats
        """)

    # Common features
    st.markdown("""
    ### Key Features:
    - Multi-select employee entry with automatic form clearing
    - Export to Daily Time and Daily Import formats
    - Support for indirect/direct employee categorization
    - Job summaries with comments (starting at row 264)
    - Columns G & M show complete Job Number - Area - Description
    - Subsistence rates automatically create additional entries
    """)

    st.markdown("---")
    st.caption("Navigate using the sidebar to access different features.")
