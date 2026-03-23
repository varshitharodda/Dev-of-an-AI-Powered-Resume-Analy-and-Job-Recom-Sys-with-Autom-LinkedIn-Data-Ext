import streamlit as st
import bcrypt
from utils.database import get_user_by_email, create_user as db_create_user, get_user_by_id, update_user_password, update_user_name

def register_user(name, email, password):

    if get_user_by_email(email):
        return False, "Email already registered."

    user_id = db_create_user(name, email, password)
    if user_id:
        return True, "Registration successful!"
    else:
        return False, "An error occurred during registration."

def login_user(email, password):
    """
    Logs in a user.
    Returns (success, message).
    """
    user = get_user_by_email(email)
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        st.session_state['logged_in'] = True
        st.session_state['user_id'] = user['id']
        st.session_state['user_name'] = user['name']
        return True, "Login successful!"
    else:
        return False, "Invalid email or password."

def change_password(user_id, current_password, new_password):
    """
    Changes the user's password.
    Returns (success, message).
    """
    user = get_user_by_id(user_id)
    if not user:
        return False, "User not found."
    
    if bcrypt.checkpw(current_password.encode('utf-8'), user['password']):
        hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        if update_user_password(user_id, hashed_new_password):
            return True, "Password changed successfully!"
        else:
            return False, "Failed to update password."
    else:
        return False, "Incorrect current password."

def update_profile_name(user_id, new_name):
    """
    Updates the user's display name.
    Returns (success, message).
    """
    if len(new_name.strip()) < 2:
        return False, "Name must be at least 2 characters long."
        
    if update_user_name(user_id, new_name.strip()):
        # Update session state immediately
        st.session_state['user_name'] = new_name.strip()
        return True, "Name updated successfully!"
    return False, "Failed to update name."

def is_user_logged_in():
    return 'logged_in' in st.session_state and st.session_state['logged_in']

def logout_user():
    """Logs out the current user."""
    if 'logged_in' in st.session_state:
        del st.session_state['logged_in']
    if 'user_id' in st.session_state:
        del st.session_state['user_id']
    if 'user_name' in st.session_state:
        del st.session_state['user_name']

def get_current_user_name():
    """Returns the name of the currently logged-in user."""
    if is_user_logged_in():
        return st.session_state['user_name']
    return None

def get_logged_in_user_id():
    """Returns the ID of the currently logged-in user."""
    if is_user_logged_in():
        return st.session_state.get('user_id')
    return None
