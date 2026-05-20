import streamlit as st
import streamlit.components.v1 as components


LOGIN_EMAIL_QUERY_PARAM = "login_email"
LOGIN_EMAIL_STORAGE_KEY = "timesheet_app_login_email"
PERSIST_EMAIL_QUERY_PARAM = "trusted_email"
PERSIST_TOKEN_QUERY_PARAM = "trusted_token"
PERSIST_EMAIL_STORAGE_KEY = "timesheet_app_trusted_email"
PERSIST_TOKEN_STORAGE_KEY = "timesheet_app_trusted_token"


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


def apply_persistent_login_memory() -> tuple[str, str]:
    """Hydrate trusted-device login details from browser storage into query params."""
    if st.session_state.pop("_clear_persistent_login", False):
        components.html(
            f"""
            <script>
            (function() {{
                const parentWindow = window.parent;
                parentWindow.localStorage.removeItem({PERSIST_EMAIL_STORAGE_KEY!r});
                parentWindow.localStorage.removeItem({PERSIST_TOKEN_STORAGE_KEY!r});
                parentWindow.sessionStorage.removeItem({PERSIST_TOKEN_STORAGE_KEY!r} + "_hydrated");
                const params = new URLSearchParams(parentWindow.location.search);
                params.delete({PERSIST_EMAIL_QUERY_PARAM!r});
                params.delete({PERSIST_TOKEN_QUERY_PARAM!r});
                const queryString = params.toString();
                const nextUrl = parentWindow.location.pathname + (queryString ? "?" + queryString : "") + parentWindow.location.hash;
                parentWindow.history.replaceState({{}}, "", nextUrl);
            }})();
            </script>
            """,
            height=0,
        )
        return "", ""

    pending = st.session_state.pop("_pending_persistent_login", None)
    if isinstance(pending, dict):
        email = str(pending.get("email", "")).strip().lower()
        token = str(pending.get("token", "")).strip()
        if email and token:
            _set_query_param(PERSIST_EMAIL_QUERY_PARAM, email)
            _set_query_param(PERSIST_TOKEN_QUERY_PARAM, token)
            components.html(
                f"""
                <script>
                (function() {{
                    const parentWindow = window.parent;
                    parentWindow.localStorage.setItem({PERSIST_EMAIL_STORAGE_KEY!r}, {email!r});
                    parentWindow.localStorage.setItem({PERSIST_TOKEN_STORAGE_KEY!r}, {token!r});
                    parentWindow.sessionStorage.setItem({PERSIST_TOKEN_STORAGE_KEY!r} + "_hydrated", "1");
                }})();
                </script>
                """,
                height=0,
            )
            return email, token

    remembered_email = _get_query_param(PERSIST_EMAIL_QUERY_PARAM).strip().lower()
    remembered_token = _get_query_param(PERSIST_TOKEN_QUERY_PARAM).strip()
    if remembered_email and remembered_token:
        return remembered_email, remembered_token

    components.html(
        f"""
        <script>
        (function() {{
            const parentWindow = window.parent;
            const params = new URLSearchParams(parentWindow.location.search);
            const email = (parentWindow.localStorage.getItem({PERSIST_EMAIL_STORAGE_KEY!r}) || "").trim().toLowerCase();
            const token = (parentWindow.localStorage.getItem({PERSIST_TOKEN_STORAGE_KEY!r}) || "").trim();
            const hydratedKey = {PERSIST_TOKEN_STORAGE_KEY!r} + "_hydrated";
            if (email && token && !params.get({PERSIST_EMAIL_QUERY_PARAM!r}) && !params.get({PERSIST_TOKEN_QUERY_PARAM!r}) && !parentWindow.sessionStorage.getItem(hydratedKey)) {{
                parentWindow.sessionStorage.setItem(hydratedKey, "1");
                params.set({PERSIST_EMAIL_QUERY_PARAM!r}, email);
                params.set({PERSIST_TOKEN_QUERY_PARAM!r}, token);
                const queryString = params.toString();
                const nextUrl = parentWindow.location.pathname + (queryString ? "?" + queryString : "") + parentWindow.location.hash;
                parentWindow.history.replaceState({{}}, "", nextUrl);
                parentWindow.location.reload();
            }}
        }})();
        </script>
        """,
        height=0,
    )
    return "", ""


def remember_login_email(email: str) -> None:
    email = str(email or "").strip().lower()
    if not email:
        return
    st.session_state["remembered_login_email"] = email
    _set_query_param(LOGIN_EMAIL_QUERY_PARAM, email)


def remember_persistent_login(email: str, token: str) -> None:
    email = str(email or "").strip().lower()
    token = str(token or "").strip()
    if not email or not token:
        return
    st.session_state["_pending_persistent_login"] = {"email": email, "token": token}


def clear_persistent_login() -> None:
    st.session_state["_clear_persistent_login"] = True
    try:
        st.query_params.pop(PERSIST_EMAIL_QUERY_PARAM, None)
        st.query_params.pop(PERSIST_TOKEN_QUERY_PARAM, None)
    except Exception:
        pass
