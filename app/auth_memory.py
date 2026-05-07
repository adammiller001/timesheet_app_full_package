import streamlit as st
import streamlit.components.v1 as components


LOGIN_EMAIL_QUERY_PARAM = "login_email"
LOGIN_EMAIL_STORAGE_KEY = "timesheet_app_login_email"


def _get_query_param(name: str) -> str:
    try:
        value = st.query_params.get(name, "")
        if isinstance(value, list):
            return str(value[0]) if value else ""
        return str(value or "")
    except Exception:
        try:
            value = st.experimental_get_query_params().get(name, [""])
            return str(value[0]) if value else ""
        except Exception:
            return ""


def _set_query_param(name: str, value: str) -> None:
    try:
        st.query_params[name] = value
        return
    except Exception:
        pass

    try:
        params = st.experimental_get_query_params()
        params[name] = value
        st.experimental_set_query_params(**params)
    except Exception:
        pass


def apply_login_email_memory() -> str:
    """Return the last login email and ask the browser to remember future entries."""
    remembered_email = _get_query_param(LOGIN_EMAIL_QUERY_PARAM).strip().lower()
    if remembered_email:
        st.session_state["remembered_login_email"] = remembered_email
    else:
        remembered_email = str(st.session_state.get("remembered_login_email", "") or "").strip().lower()

    components.html(
        f"""
        <script>
        (function() {{
            const storageKey = {LOGIN_EMAIL_STORAGE_KEY!r};
            const queryName = {LOGIN_EMAIL_QUERY_PARAM!r};
            const parentWindow = window.parent;
            const params = new URLSearchParams(parentWindow.location.search);
            const queryEmail = (params.get(queryName) || "").trim().toLowerCase();
            if (queryEmail) {{
                parentWindow.localStorage.setItem(storageKey, queryEmail);
            }}

            const savedEmail = (parentWindow.localStorage.getItem(storageKey) || "").trim().toLowerCase();
            if (savedEmail && !queryEmail && !parentWindow.sessionStorage.getItem(storageKey + "_hydrated")) {{
                parentWindow.sessionStorage.setItem(storageKey + "_hydrated", "1");
                params.set(queryName, savedEmail);
                const queryString = params.toString();
                const nextUrl = parentWindow.location.pathname + (queryString ? "?" + queryString : "") + parentWindow.location.hash;
                parentWindow.history.replaceState({{}}, "", nextUrl);
                parentWindow.location.reload();
                return;
            }}

            function wireEmailInput() {{
                const inputs = parentWindow.document.querySelectorAll("input");
                for (const input of inputs) {{
                    const placeholder = (input.getAttribute("placeholder") || "").toLowerCase();
                    const label = (input.getAttribute("aria-label") || "").toLowerCase();
                    if (placeholder.includes("ptwenergy") || label.includes("email")) {{
                        input.setAttribute("autocomplete", "email");
                        input.setAttribute("name", "email");
                        input.addEventListener("change", function() {{
                            const email = (input.value || "").trim().toLowerCase();
                            if (email) parentWindow.localStorage.setItem(storageKey, email);
                        }});
                    }}
                }}
            }}

            setTimeout(wireEmailInput, 250);
            setTimeout(wireEmailInput, 1000);
        }})();
        </script>
        """,
        height=0,
    )
    return remembered_email


def remember_login_email(email: str) -> None:
    email = str(email or "").strip().lower()
    if not email:
        return
    st.session_state["remembered_login_email"] = email
    _set_query_param(LOGIN_EMAIL_QUERY_PARAM, email)
