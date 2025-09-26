import streamlit as st
import pandas as pd
from pathlib import Path
import tempfile
import shutil
from io import BytesIO
import time

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
    page_icon="⏰",
    layout="wide"
)


def safe_read_excel(file_path, sheet_name, force_refresh=False):
    """Safely read Excel file with fallback for permission issues and force refresh option"""
    try:
        # Add timestamp to force fresh read
        if force_refresh:
            # Force a fresh file read by accessing file stats
            file_path = Path(file_path)
            if file_path.exists():
                _ = file_path.stat().st_mtime
        return pd.read_excel(file_path, sheet_name=sheet_name)
    except PermissionError:
        try:
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                shutil.copy2(file_path, tmp.name)
                result = pd.read_excel(tmp.name, sheet_name=sheet_name)
                return result
        except Exception as e:
            st.error(f"Could not read Excel file. Error: {e}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        return pd.DataFrame()

def load_users(force_refresh=False):
    """Load users from Google Sheets when available, fallback to Excel"""
    google_error = None
    sheet_candidates = ("Users", "User")

    if (
        HAVE_GOOGLE_SHEETS
        and read_timesheet_data
        and "google_sheets_id" in st.secrets
        and st.secrets["google_sheets_id"]
    ):
        sheet_id = st.secrets["google_sheets_id"]
        manager = get_sheets_manager()
        if force_refresh and hasattr(manager, "spreadsheet"):
            manager.spreadsheet = None
        worksheet, actual_title = manager.find_worksheet(sheet_candidates, sheet_id)

        if worksheet and actual_title:
            try:
                users_df = manager.read_worksheet(actual_title, sheet_id)
                if not users_df.empty:
                    return users_df, None
                else:
                    google_error = f"Google Sheets worksheet '{actual_title}' is empty"
            except Exception as e:
                google_error = f"Google Sheets error: {e}"
                st.warning(f"Google Sheets unavailable, falling back to Excel: {e}")
        else:
            google_error = "Users worksheet not found in Google Sheets"

    excel_path = Path(__file__).parent / "TimeSheet Apps.xlsx"
    if not excel_path.exists():
        return pd.DataFrame(), (google_error or "Excel file not found")

    try:
        available_sheets = pd.ExcelFile(excel_path).sheet_names
    except Exception as e:
        message = f"Unable to read Excel workbook: {e}"
        if google_error:
            message = f"{google_error}. {message}"
        return pd.DataFrame(), message

    def _match_sheet_name(target, sheets):
        target_norm = target.strip().lower()
        for sheet in sheets:
            if sheet.strip().lower() == target_norm:
                return sheet
        return None

    for candidate in sheet_candidates:
        sheet_name = _match_sheet_name(candidate, available_sheets)
        if sheet_name:
            try:
                users_df = safe_read_excel(excel_path, sheet_name, force_refresh=force_refresh)
                if not users_df.empty:
                    users_df.columns = [str(col).strip() for col in users_df.columns]
                    return users_df, None
            except Exception:
                # safe_read_excel already surfaces a user-facing error
                continue

    message = "Users worksheet is empty"
    if google_error:
        message = f"{message} (previous issue: {google_error})"
    return pd.DataFrame(), message

def authenticate_user(email, force_refresh=False):
    """Check if user email exists in Users worksheet and return user type"""
    users_df, error = load_users(force_refresh=force_refresh)
    if error:
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

    # Check if Excel file exists (silently)
    excel_path = Path(__file__).parent / "TimeSheet Apps.xlsx"
    if not excel_path.exists():
        st.error("⚠️ TimeSheet Apps.xlsx not found - Please contact your administrator")
        st.stop()

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
        - **📊 What's Been Added Today** - View today's entries *(Admin Access)*
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