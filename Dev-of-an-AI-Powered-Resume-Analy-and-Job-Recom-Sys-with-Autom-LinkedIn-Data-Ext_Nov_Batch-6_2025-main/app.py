import streamlit as st
from frontend.pages import LOGGED_IN_PAGES
from backend.auth import is_user_logged_in, logout_user
from frontend import login, registration

# Ensure database tables and data directories exist on startup
from utils.database import create_tables
from frontend.modern_components import init_modern_ui

# Initialize DB and required directories (idempotent)
create_tables()


def main():
    st.set_page_config(layout="wide", page_title="Resume Analyst & Job Recommender")
    init_modern_ui()
    st.sidebar.title("Navigation")

    # Icon mapping for navigation labels
    ICONS = {
        "Dashboard": "🏠",
        "My Profile": "👤",
        "Resume Analysis": "📝",
        "Analysis Results": "📊",
        "Resume Scoring": "🎯",
        "Skills Gap Analysis": "🔍",
        "Job Recommendations": "💼",
        "Settings": "⚙️",
        "Login": "🔐",
        "Registration": "✍️",
        "Logout": "🚪",
    }

    if 'page' not in st.session_state:
        st.session_state['page'] = 'Login' if not is_user_logged_in() else 'Dashboard'

    if is_user_logged_in():
        pages = LOGGED_IN_PAGES
        page_names = list(pages.keys())

        # If current page is not valid for logged-in state, default to Dashboard
        if st.session_state.get('page') not in pages:
            st.session_state['page'] = 'Dashboard'

        # Logout with icon
        if st.sidebar.button(f"{ICONS.get('Logout','')} Logout"):
            logout_user()
            st.session_state['page'] = 'Login'
            st.rerun()

        st.sidebar.divider()

        # Navigation buttons with icons; highlight current page
        for page_name in page_names:
            label = f"{ICONS.get(page_name, '')} {page_name}"
            if page_name == st.session_state.get('page'):
                # Render highlighted static label for active page
                st.sidebar.markdown(
                    f"<div style='background: linear-gradient(90deg, var(--primary-color), #a78bfa); color: white; padding: 0.6rem; border-radius: 8px; font-weight: 700; text-align: left; margin-bottom: 0.5rem;'>{ICONS.get(page_name, '')} {page_name}</div>",
                    unsafe_allow_html=True
                )
            else:
                if st.sidebar.button(label, use_container_width=True):
                    st.session_state['page'] = page_name
                    st.rerun()

    else:
        pages = {
            "Login": login.login_page,
            "Registration": registration.registration_page
        }

        # If current page is not valid for logged-out state, default to Login
        if st.session_state.get('page') not in pages:
            st.session_state['page'] = 'Login'

        for page_name in pages.keys():
            label = f"{ICONS.get(page_name, '')} {page_name}"
            if page_name == st.session_state.get('page'):
                st.sidebar.markdown(
                    f"<div style='background: linear-gradient(90deg, var(--primary-color), #a78bfa); color: white; padding: 0.6rem; border-radius: 8px; font-weight: 700; text-align: left; margin-bottom: 0.5rem;'>{ICONS.get(page_name, '')} {page_name}</div>",
                    unsafe_allow_html=True
                )
            else:
                if st.sidebar.button(label, use_container_width=True):
                    st.session_state['page'] = page_name
                    st.rerun()
    # Safely render the resolved page
    pages[st.session_state['page']]()

if __name__ == "__main__":
    main()
