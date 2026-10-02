import streamlit as st
from app.auth_memory import (
    apply_login_email_memory,
    apply_persistent_login_memory,
    clear_persistent_login,
    remember_login_email,
    remember_persistent_login,
)
from app.auth_users import (
    add_remember_token,
    authenticate_remembered_device,
    authenticate_user as authenticate_user_with_pin,
    create_user_pin,
    get_login_status,
)
from app.style_utils import apply_app_theme, apply_watermark

# Configure page
st.set_page_config(
    page_title="Field Reports Suite",
    page_icon="⏰",
    layout="wide"
)

apply_app_theme()
apply_watermark()


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

trusted_email, trusted_token = apply_persistent_login_memory()
if not st.session_state.get("authenticated", False) and trusted_email and trusted_token:
    trusted_result = authenticate_remembered_device(trusted_email, trusted_token, force_refresh=True)
    if trusted_result.ok:
        remember_login_email(trusted_email)
        st.session_state["user_email"] = trusted_email
        st.session_state["user_type"] = trusted_result.user_type
        st.session_state["authenticated"] = True
        st.rerun()
    else:
        clear_persistent_login()

# Show login form if not authenticated
if not st.session_state.get("authenticated", False):
    st.markdown("""<style>.block-container {padding-top: 9rem !important;}@media (max-width: 768px){.block-container {padding-top: 6rem !important;}}</style>""", unsafe_allow_html=True)
    st.title("Field Reports Suite")
    st.markdown("### Please sign in with your work email")

    remembered_email = apply_login_email_memory()
    if remembered_email and "login_email_input" not in st.session_state:
        st.session_state["login_email_input"] = remembered_email

    with st.form("login_form"):
        email = st.text_input("Email Address", placeholder="you@ptwenergy.com", key="login_email_input").strip().lower()
        pin = st.text_input("PIN", max_chars=4, type="password", key="login_pin_input")
        st.caption("First time signing in? Create a 4-digit PIN below.")
        create_pin_value = st.text_input("Create PIN", max_chars=4, type="password", key="create_pin_input")
        confirm_pin_value = st.text_input("Confirm PIN", max_chars=4, type="password", key="confirm_pin_input")
        keep_logged_in = st.checkbox("Keep me logged in on this device", key="keep_logged_in_checkbox")
        submitted = st.form_submit_button("Sign In", type="primary")

        if submitted:
            if not email:
                st.error("Please enter your email address")
            else:
                status = get_login_status(email, force_refresh=True)
                if not status.ok:
                    st.error(f"Access denied: {status.error}")
                    st.info("Please contact your administrator if you believe this is an error")
                elif status.needs_pin_setup:
                    result = create_user_pin(email, create_pin_value, confirm_pin_value, force_refresh=True)
                    if not result.ok:
                        st.error(result.error or "Could not create PIN.")
                    else:
                        if keep_logged_in:
                            token = add_remember_token(email, force_refresh=True)
                            if token:
                                remember_persistent_login(email, token)
                        remember_login_email(email)
                        st.session_state["user_email"] = email
                        st.session_state["user_type"] = result.user_type
                        st.session_state["authenticated"] = True
                        st.success(f"Welcome! Signed in as {result.user_type}")
                        st.rerun()
                else:
                    result = authenticate_user_with_pin(email, pin, force_refresh=True)
                    if result.ok:
                        if keep_logged_in:
                            token = add_remember_token(email, force_refresh=True)
                            if token:
                                remember_persistent_login(email, token)
                        remember_login_email(email)
                        st.session_state["user_email"] = email
                        st.session_state["user_type"] = result.user_type
                        st.session_state["authenticated"] = True
                        st.success(f"Welcome! Signed in as {result.user_type}")
                        st.rerun()
                    else:
                        st.error(result.error or "Access denied.")
                        st.info("Please contact your administrator if you believe this is an error")

else:
    st.markdown("""<style>.block-container {padding-top: 2rem !important;}</style>""", unsafe_allow_html=True)
    # User is authenticated - show main app
    st.title("Field Reports Suite")

    # Show user info in sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown("**Signed in as:**")
        st.markdown(st.session_state["user_email"])
        st.markdown(st.session_state["user_type"])

        if st.button("Sign Out"):
            clear_persistent_login()
            st.session_state["user_email"] = None
            st.session_state["user_type"] = None
            st.session_state["authenticated"] = False
            st.rerun()

        st.markdown("---")

    # Welcome message
    user_type = st.session_state.get("user_type", "User")
    st.write(f"Welcome to the Field Reports Suite, {user_type}!")


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


