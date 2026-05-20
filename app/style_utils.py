import base64
from pathlib import Path
import streamlit as st


WATERMARK_KEY = "_watermark_injected"


def apply_app_theme(page_width: int = 1120):
    """Apply the shared PTW form-style theme across Streamlit pages."""
    st.markdown(
        f"""
        <style>
        :root {{
            --ptw-bg: #e9e9e9;
            --ptw-panel: #f4f4f5;
            --ptw-blue: #304d9a;
            --ptw-blue-dark: #223a7a;
            --ptw-text: #111827;
            --ptw-muted: #6b7280;
            --ptw-border: #9ca3af;
            --ptw-danger: #df4f4f;
        }}
        [data-testid="stAppViewContainer"] {{
            background: var(--ptw-bg) !important;
        }}
        section.main > div {{
            max-width: {page_width}px;
            padding-top: 1.25rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }}
        h1, h2, h3 {{
            color: var(--ptw-text) !important;
            letter-spacing: 0 !important;
        }}
        h1 {{
            font-size: 28px !important;
            font-weight: 700 !important;
            margin-bottom: 1.35rem !important;
        }}
        h2, h3 {{
            font-weight: 700 !important;
        }}
        p, span, label, div {{
            letter-spacing: 0 !important;
        }}
        div[data-testid="stCaptionContainer"] {{
            color: var(--ptw-muted) !important;
        }}
        label[data-testid="stWidgetLabel"] {{
            align-items: center;
            background: var(--ptw-blue);
            border: 1px solid var(--ptw-blue-dark);
            color: #ffffff !important;
            display: flex;
            font-size: 13px;
            font-weight: 700;
            min-height: 28px;
            line-height: 1;
            margin-bottom: 0 !important;
            padding: 0 7px;
            width: 100%;
        }}
        label[data-testid="stWidgetLabel"] p {{
            color: #ffffff !important;
            font-size: 13px !important;
            font-weight: 700 !important;
        }}
        div[data-testid="stDateInput"] input,
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-baseweb="select"] > div,
        div[data-baseweb="tag"] {{
            border-radius: 0 !important;
        }}
        div[data-testid="stDateInput"] input,
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stTextArea"] textarea {{
            background: #ffffff !important;
            border: 1px solid var(--ptw-border) !important;
            min-height: 28px !important;
        }}
        div[data-baseweb="select"] > div {{
            background: #ffffff !important;
            border-color: var(--ptw-blue) !important;
            min-height: 28px !important;
        }}
        div[data-testid="stButton"] button,
        div[data-testid="stDownloadButton"] button,
        button[data-testid^="stBaseButton"]:not([kind^="header"]) {{
            border-radius: 2px !important;
            min-height: 30px;
            padding-bottom: 4px;
            padding-top: 4px;
        }}
        div[data-testid="stButton"] button[kind="primary"],
        div[data-testid="stDownloadButton"] button[kind="primary"],
        button[kind*="primary"]:not([kind^="header"]),
        button[kind*="FormSubmit"] {{
            background: var(--ptw-danger) !important;
            border-color: var(--ptw-danger) !important;
            color: #ffffff !important;
        }}
        div[data-testid="stHorizontalBlock"] {{
            gap: 0.25rem;
        }}
        div[data-testid="stDataFrame"],
        div[data-testid="stDataEditor"],
        div[data-testid="stTable"] {{
            border: 1px solid #d1d5db;
            border-radius: 0;
            overflow: hidden;
            background: #ffffff;
        }}
        div[data-testid="stTabs"] button {{
            border-radius: 0 !important;
            color: var(--ptw-text) !important;
        }}
        div[data-testid="stTabs"] button[aria-selected="true"] {{
            color: var(--ptw-blue) !important;
            font-weight: 700 !important;
        }}
        [data-testid="stSidebar"] {{
            background: #e5e7eb !important;
        }}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
            color: var(--ptw-text);
        }}
        .legacy-entry-title,
        .ptw-page-title {{
            color: var(--ptw-text);
            font-size: 28px;
            font-weight: 700;
            margin: 0 0 18px 0;
        }}
        .legacy-row-label,
        .ptw-field-label {{
            align-items: center;
            background: var(--ptw-blue);
            border: 1px solid var(--ptw-blue-dark);
            color: #ffffff;
            display: flex;
            font-size: 13px;
            font-weight: 700;
            min-height: 28px;
            line-height: 1;
            padding: 0 7px;
            width: 100%;
        }}
        .legacy-spacer,
        .ptw-spacer {{
            height: 4px;
        }}
        .ptw-section {{
            border-top: 1px solid #c7c7c7;
            margin-top: 1.75rem;
            padding-top: 1.25rem;
        }}
        .ptw-toolbar {{
            align-items: end;
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }}
        .stAlert {{
            border-radius: 0 !important;
        }}
        @media (max-width: 768px) {{
            section.main > div {{
                padding-left: 1rem;
                padding-right: 1rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_title(title: str):
    st.markdown(f'<div class="ptw-page-title">{title}</div>', unsafe_allow_html=True)


def apply_watermark(image_path: str = "PTW.jpg", opacity: float = 0.12, max_size: int = 480):
    """Render a subtle background watermark for the entire Streamlit app."""
    try:
        img_path = Path(image_path)
        if not img_path.exists():
            st.warning(f"Watermark image not found: {img_path}")
            return

        encoded = base64.b64encode(img_path.read_bytes()).decode()
        css = f"""
            <style>
            [data-testid="stAppViewContainer"]::before {{
                content: "";
                position: fixed;
                inset: 0;
                background-image: url('data:image/jpeg;base64,{encoded}');
                background-repeat: no-repeat;
                background-position: center center;
                background-size: min({max_size}px, 60vmin);
                opacity: {opacity};
                pointer-events: none;
                z-index: 0;
            }}
            section.main > div {{
                position: relative;
                z-index: 1;
            }}
            </style>
        """
        st.markdown(css, unsafe_allow_html=True)
        st.session_state[WATERMARK_KEY] = True
    except Exception as e:
        st.warning(f"Could not apply watermark: {e}")
