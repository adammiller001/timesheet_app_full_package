import base64
from pathlib import Path
import streamlit as st


WATERMARK_KEY = "_watermark_injected"


def apply_watermark(image_path: str = "PTW.jpg", opacity: float = 0.12, max_size: int = 480):
    """Render a subtle background watermark for the entire Streamlit app."""
    if st.session_state.get(WATERMARK_KEY):
        return

    try:
        img_path = Path(image_path)
        if not img_path.exists():
            st.warning(f"Watermark image not found: {img_path}")
            return

        encoded = base64.b64encode(img_path.read_bytes()).decode()
        css = f"""
            <style>
            [data-testid="stAppViewContainer"] {{
                background: transparent !important;
            }}
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
