import streamlit as st
import re
from datetime import datetime
from database import DatabaseManager
from logger import app_logger, LoggingContextManager, log_exception

def validate_password(password):
    """Validate password strength"""
    # Minimum length 8 characters
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    # Check for at least one uppercase letter
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for at least one lowercase letter
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for at least one digit
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    # Check for at least one special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password meets requirements"

def validate_username(username):
    """Validate username format"""
    # Username must be 3-20 characters long and contain only letters, numbers, underscores
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return False, "Username must be 3-20 characters long and contain only letters, numbers, and underscores"
    
    return True, "Username is valid"

def user_management_page():
    """User management page for administrators"""
    with LoggingContextManager(app_logger, "user_management_page"):
        app_logger.debug("Rendering User Management page")
        st.title("👤 User Management")
        st.markdown("---")
        
        if st.session_state.user['username'] not in ['admin', 'sana']:
            st.warning("⚠️ You don't have permission to access the user management features.")
            return
        
        db = DatabaseManager()
        current_user_id = st.session_state.user['id']
        
        tabs = st.tabs(["👥 All Users", "➕ Add User", "✏️ My Profile"])
        
        # All Users Tab
        with tabs[0]:
            st.subheader("All Users")
            
            try:
                users = db.get_all_users()
                
                if not users:
                    st.info("No users found in the system.")
                else:
                    # Create a formatted table for display
                    user_table = []
                    for user in users:
                        created_date = datetime.fromisoformat(user["created_at"]) if isinstance(user["created_at"], str) else user["created_at"]
                        created_date_str = created_date.strftime("%Y-%m-%d") if created_date else "N/A"
                        
                        # Add row to table
                        user_table.append({
                            "ID": user["id"],
                            "Username": user["username"],
                            "Full Name": user["full_name"],
                            "Created On": created_date_str
                        })
                    
                    st.dataframe(user_table, use_container_width=True, hide_index=True)
                    
                    # User action section
                    st.markdown("---")
                    st.subheader("User Actions")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        selected_user = st.selectbox(
                            "Select User", 
                            options=[f"{u['username']} ({u['full_name']})" for u in users],
                            index=0
                        )
                        selected_username = selected_user.split(" ")[0]
                        selected_user_id = next((u["id"] for u in users if u["username"] == selected_username), None)
                    
                    with col2:
                        action = st.selectbox(
                            "Action",
                            options=["Change Username", "Reset Password", "Change Full Name", "Delete User"]
                        )
                    
                    if selected_user_id == current_user_id and action == "Delete User":
                        st.error("⚠️ You cannot delete your own account.")
                    else:
                        with st.form("user_action_form"):
                            if action == "Change Username":
                                new_username = st.text_input("New Username")
                                
                                submit = st.form_submit_button("Update Username", use_container_width=True, type="primary")
                                
                                if submit:
                                    if not new_username:
                                        st.error("Username cannot be empty.")
                                    else:
                                        valid, message = validate_username(new_username)
                                        if not valid:
                                            st.error(message)
                                        else:
                                            success, message = db.update_username(selected_user_id, new_username)
                                            if success:
                                                st.success(f"✅ Username updated successfully.")
                                                # If current user's username was changed, update session
                                                if selected_user_id == current_user_id:
                                                    st.session_state.user["username"] = new_username
                                                st.rerun()
                                            else:
                                                st.error(f"❌ {message}")
                            
                            elif action == "Reset Password":
                                # For admin reset, we don't need the current password
                                new_password = st.text_input("New Password", type="password")
                                confirm_password = st.text_input("Confirm Password", type="password")
                                
                                submit = st.form_submit_button("Reset Password", use_container_width=True, type="primary")
                                
                                if submit:
                                    if not new_password or not confirm_password:
                                        st.error("Password fields cannot be empty.")
                                    elif new_password != confirm_password:
                                        st.error("Passwords do not match.")
                                    else:
                                        valid, message = validate_password(new_password)
                                        if not valid:
                                            st.error(message)
                                        else:
                                            # For admin reset, we'll use a dummy current password and override the check
                                            conn = db.get_connection()
                                            cursor = conn.cursor()
                                            
                                            try:
                                                import hashlib
                                                new_hash = hashlib.sha256(new_password.encode()).hexdigest()
                                                
                                                cursor.execute('''
                                                    UPDATE users
                                                    SET password_hash = ?
                                                    WHERE id = ?
                                                ''', (new_hash, selected_user_id))
                                                
                                                conn.commit()
                                                
                                                st.success(f"✅ Password reset successfully.")
                                                app_logger.info(f"Password reset for user ID={selected_user_id} by admin (ID={current_user_id})")
                                            except Exception as e:
                                                conn.rollback()
                                                app_logger.error(f"Error resetting password: {str(e)}")
                                                st.error(f"❌ Error resetting password: {str(e)}")
                                            finally:
                                                conn.close()
                            
                            elif action == "Change Full Name":
                                # Get current full name
                                current_full_name = next((u["full_name"] for u in users if u["id"] == selected_user_id), "")
                                
                                new_full_name = st.text_input("New Full Name", value=current_full_name)
                                
                                submit = st.form_submit_button("Update Full Name", use_container_width=True, type="primary")
                                
                                if submit:
                                    if not new_full_name:
                                        st.error("Full name cannot be empty.")
                                    else:
                                        success, message = db.update_full_name(selected_user_id, new_full_name)
                                        if success:
                                            st.success(f"✅ Full name updated successfully.")
                                            # If current user's name was changed, update session
                                            if selected_user_id == current_user_id:
                                                st.session_state.user["full_name"] = new_full_name
                                            st.rerun()
                                        else:
                                            st.error(f"❌ {message}")
                            
                            elif action == "Delete User":
                                st.warning("⚠️ This will delete the user but keep their expenses in the system.")
                                confirm_delete = st.checkbox("I understand this action is irreversible")
                                
                                submit = st.form_submit_button("Delete User", use_container_width=True, type="primary", disabled=not confirm_delete)
                                
                                if submit:
                                    success, message = db.delete_user(selected_user_id)
                                    if success:
                                        st.success(f"✅ {message}")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {message}")
            
            except Exception as e:
                app_logger.error(f"Error in user management page: {str(e)}")
                log_exception(app_logger, e, "user management page")
                st.error(f"An error occurred: {str(e)}")
        
        # Add User Tab
        with tabs[1]:
            st.subheader("Add New User")
            
            with st.form("add_user_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_username = st.text_input("Username")
                    new_full_name = st.text_input("Full Name")
                
                with col2:
                    new_password = st.text_input("Password", type="password")
                    confirm_password = st.text_input("Confirm Password", type="password")
                
                st.markdown("Password must have at least 8 characters with uppercase, lowercase, digit, and special character.")
                
                submit_add = st.form_submit_button("Add User", use_container_width=True, type="primary")
                
                if submit_add:
                    if not new_username or not new_full_name or not new_password or not confirm_password:
                        st.error("All fields are required.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        valid_username, username_message = validate_username(new_username)
                        valid_password, password_message = validate_password(new_password)
                        
                        if not valid_username:
                            st.error(username_message)
                        elif not valid_password:
                            st.error(password_message)
                        else:
                            try:
                                success, result = db.add_user(new_username, new_password, new_full_name)
                                if success:
                                    st.success(f"✅ User '{new_username}' added successfully!")
                                    st.balloons()
                                else:
                                    st.error(f"❌ {result}")
                            except Exception as e:
                                app_logger.error(f"Error adding new user: {str(e)}")
                                st.error(f"❌ Error adding user: {str(e)}")
        
        # My Profile Tab
        with tabs[2]:
            st.subheader("My Profile")
            
            # Get current user details
            user = db.get_user_by_id(current_user_id)
            
            if user:
                # Display current user info
                st.info(f"""
                **Current User Information**
                - **Username:** {user['username']}
                - **Full Name:** {user['full_name']}
                - **User ID:** {user['id']}
                - **Account Created:** {datetime.fromisoformat(user['created_at']).strftime('%Y-%m-%d') if isinstance(user['created_at'], str) else user['created_at']}
                """)
                
                st.markdown("---")
                
                profile_tabs = st.tabs(["Change Password", "Update Profile"])
                
                # Password Change Tab
                with profile_tabs[0]:
                    with st.form("change_password_form"):
                        st.subheader("Change Your Password")
                        
                        current_pwd = st.text_input("Current Password", type="password")
                        new_pwd = st.text_input("New Password", type="password")
                        confirm_pwd = st.text_input("Confirm New Password", type="password")
                        
                        st.markdown("Password must have at least 8 characters with uppercase, lowercase, digit, and special character.")
                        
                        submit_pwd = st.form_submit_button("Update Password", use_container_width=True, type="primary")
                        
                        if submit_pwd:
                            if not current_pwd or not new_pwd or not confirm_pwd:
                                st.error("All password fields are required.")
                            elif new_pwd != confirm_pwd:
                                st.error("New passwords do not match.")
                            else:
                                valid, message = validate_password(new_pwd)
                                if not valid:
                                    st.error(message)
                                else:
                                    success, message = db.update_password(current_user_id, current_pwd, new_pwd)
                                    if success:
                                        st.success("✅ Password updated successfully!")
                                    else:
                                        st.error(f"❌ {message}")
                
                # Profile Update Tab
                with profile_tabs[1]:
                    with st.form("update_profile_form"):
                        st.subheader("Update Your Profile")
                        
                        # Username update
                        new_username = st.text_input("New Username", value=user['username'])
                        
                        # Full name update
                        new_full_name = st.text_input("Full Name", value=user['full_name'])
                        
                        submit_profile = st.form_submit_button("Update Profile", use_container_width=True, type="primary")
                        
                        if submit_profile:
                            # Check if username changed
                            username_updated = False
                            fullname_updated = False
                            
                            if new_username != user['username']:
                                valid, message = validate_username(new_username)
                                if not valid:
                                    st.error(message)
                                else:
                                    success, message = db.update_username(current_user_id, new_username)
                                    if success:
                                        username_updated = True
                                        # Update session state
                                        st.session_state.user["username"] = new_username
                                    else:
                                        st.error(f"Failed to update username: {message}")
                            
                            # Check if full name changed
                            if new_full_name != user['full_name']:
                                if not new_full_name.strip():
                                    st.error("Full name cannot be empty.")
                                else:
                                    success, message = db.update_full_name(current_user_id, new_full_name)
                                    if success:
                                        fullname_updated = True
                                        # Update session state
                                        st.session_state.user["full_name"] = new_full_name
                                    else:
                                        st.error(f"Failed to update full name: {message}")
                            
                            # Success message if anything was updated
                            if username_updated or fullname_updated:
                                st.success("✅ Profile updated successfully!")
                                st.rerun()
                            elif not username_updated and new_username == user['username'] and \
                                 not fullname_updated and new_full_name == user['full_name']:
                                st.info("No changes were made.")
            else:
                st.error("Unable to retrieve user information.")


# For testing when run directly
if __name__ == "__main__":
    # Simulate logged in user
    if 'user' not in st.session_state:
        st.session_state.user = {'id': 1, 'username': 'admin', 'full_name': 'Admin User'}
    
    # Set page config
    st.set_page_config(page_title="User Management", page_icon="👤", layout="wide")
    
    user_management_page()
