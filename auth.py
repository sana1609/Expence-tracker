import streamlit as st
from database import DatabaseManager
from logger import auth_logger, LoggingContextManager

def init_session_state():
    """Initialize session state variables"""
    with LoggingContextManager(auth_logger, "init_session_state"):
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
            auth_logger.debug("Initialized authenticated state to False")
        if 'user' not in st.session_state:
            st.session_state.user = None
            auth_logger.debug("Initialized user state to None")

def login_page():
    """Display login page"""
    auth_logger.debug("Rendering login page")
    st.title("🏦 Expense Tracker Login")
    st.markdown("---")
    
    with st.form("login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.subheader("Please Login")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            submitted = st.form_submit_button("Login", use_container_width=True)
            
            if submitted:
                auth_logger.info(f"Login attempt for username: {username}")
                if username and password:
                    try:
                        db = DatabaseManager()
                        user = db.authenticate_user(username, password)
                        
                        if user:
                            st.session_state.authenticated = True
                            st.session_state.user = user
                            auth_logger.info(f"User '{username}' logged in successfully")
                            st.success(f"Welcome, {user['full_name']}!")
                            st.rerun()
                        else:
                            auth_logger.warning(f"Failed login attempt for username: {username}")
                            st.error("Invalid username or password")
                    except Exception as e:
                        auth_logger.error(f"Error during login: {str(e)}")
                        st.error("An error occurred during login. Please try again.")
                else:
                    auth_logger.warning("Login attempt with empty credentials")
                    st.error("Please enter both username and password")

def logout():
    """Logout user"""
    if st.session_state.authenticated and st.session_state.user:
        username = st.session_state.user.get('username', 'Unknown')
        auth_logger.info(f"User '{username}' logged out")
    
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()

def require_auth(func):
    """Decorator to require authentication"""
    def wrapper(*args, **kwargs):
        if not st.session_state.authenticated:
            auth_logger.debug(f"Unauthenticated access attempt to {func.__name__}")
            login_page()
            return
        
        auth_logger.debug(f"Authenticated access to {func.__name__} by user '{st.session_state.user.get('username', 'Unknown')}'")
        return func(*args, **kwargs)
    return wrapper