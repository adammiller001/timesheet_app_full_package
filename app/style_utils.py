import base64
from pathlib import Path
import streamlit as st


WATERMARK_KEY = "_watermark_injected"


def apply_watermark(image_path: str = "PTW.jpg", opacity: float = 0.08):
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
            [data-testid="stAppViewContainer"]::before {{
                content: "";
                background: url('data:image/jpeg;base64,{encoded}') no-repeat center center fixed;
                background-size: contain;
                opacity: {opacity};
                position: fixed;
                inset: 0;
                pointer-events: none;
                z-index: -1;
            }}
            </style>
        """
        st.markdown(css, unsafe_allow_html=True)
        st.session_state[WATERMARK_KEY] = True
    except Exception as e:
        st.warning(f"Could not apply watermark: {e}")
