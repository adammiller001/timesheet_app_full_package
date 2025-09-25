import streamlit as st
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="PTW - Daily Timesheet Suite",
    page_icon="⏰",
    layout="wide"
)

# Skip authentication for cloud deployment
if "user_email" not in st.session_state:
    st.session_state["user_email"] = "user@ptwenergy.com"

# Main app content
st.title("📊 PTW - Daily Timesheet Suite")
st.write("Welcome to the PTW Timesheet Management System!")

# Check if Excel file exists
excel_path = Path(__file__).parent / "Timesheet Apps.xlsx"
if excel_path.exists():
    st.success("✅ Timesheet Apps.xlsx found and ready to use")
else:
    st.warning("⚠️ Timesheet Apps.xlsx not found")
    st.info("Please ensure the Excel file is uploaded to your repository")

# Navigation instructions
st.markdown("---")
st.markdown("### Available Pages")
st.markdown("""
Use the sidebar to navigate to different features:

- **📝 Timesheet Entry** - Add and manage time entries
- **📊 What's Been Added Today** - View today's entries
- **📤 Export Day** - Generate Daily Time and Daily Import reports
- **⚙️ Admin** - Administrative functions

### Key Features:
- Multi-select employee entry with automatic form clearing
- Export to Daily Time and Daily Import formats
- Support for indirect/direct employee categorization
- Job summaries with comments (starting at row 264)
- Columns G & M show complete Job Number - Area - Description
- Subsistence rates automatically create additional entries
""")

st.markdown("---")
st.info(f"Current user: {st.session_state.get('user_email', 'Not set')}")
st.caption("Navigate using the sidebar to access different features.")