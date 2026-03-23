import streamlit as st
from backend.auth import login_user, is_user_logged_in, logout_user, get_current_user_name

def login_page():
    if is_user_logged_in():
        st.title(f"Welcome, {get_current_user_name()}!")
        st.button("Logout", on_click=logout_user)
        st.success("You are logged in.")
    else:
        st.title("Login to Your Account")

        with st.form("login_form"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                success, message = login_user(email, password)
                if success:
                    st.rerun()
                else:
                    st.error(message)
