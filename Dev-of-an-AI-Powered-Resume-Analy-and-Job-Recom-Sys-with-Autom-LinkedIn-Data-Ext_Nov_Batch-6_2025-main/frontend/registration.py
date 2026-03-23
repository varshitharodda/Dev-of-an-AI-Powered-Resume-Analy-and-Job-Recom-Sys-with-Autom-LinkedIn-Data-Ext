import re
from backend.auth import *

def is_valid_email(email):
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email)

def is_strong_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character."
    return True, ""

def registration_page():
    st.title("Create an Account")

    with st.form("registration_form"):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        submitted = st.form_submit_button("Register")

        if submitted:
            error = False
            if not full_name:
                st.error("Full Name is required.")
                error = True
            elif not all(x.isalpha() or x.isspace() for x in full_name):
                 st.error("Name should contain only letters.")
                 error = True

            if not email:
                st.error("Email is required.")
                error = True
            elif not is_valid_email(email):
                st.error("Invalid email format.")
                error = True

            is_strong, message = is_strong_password(password)
            if not is_strong:
                st.error(message)
                error = True

            if password != confirm_password:
                st.error("Passwords do not match.")
                error = True

            if not error:
                success, message = register_user(full_name, email, password)
                if success:
                    st.success(message + " Redirecting to Login...")
                    st.session_state['page'] = 'Login'
                    st.rerun()
                else:
                    st.error(message)
