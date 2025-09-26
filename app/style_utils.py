import base64
from pathlib import Path
import streamlit as st


def apply_watermark(image_path: str = "PTW.jpg", opacity: float = 0.08):
    """Render a subtle background watermark for the entire Streamlit app."""
    try:
        img_path = Path(image_path)
        if not img_path.exists():
            st.warning(f"Watermark image not found: {img_path}")
            return

        encoded = base64.b64encode(img_path.read_bytes()).decode()
        css = f"""
            <style>
            div[data-testid="stAppViewContainer"] {{
                position: relative;
            }}
            div[data-testid="stAppViewContainer"]::before {{
                content: "";
                background: url('data:image/jpeg;base64,{encoded}') no-repeat center center fixed;
                background-size: contain;
                opacity: {opacity};
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                pointer-events: none;
                z-index: -1;
            }}
            </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Could not apply watermark: {e}")
