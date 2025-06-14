import streamlit as st
from database import DatabaseManager
from utils import EXPENSE_CATEGORIES, format_currency
from datetime import datetime
from logger import app_logger, LoggingContextManager, log_exception

def manage_expense_page():
    """
    Page for managing (updating and deleting) expenses
    """
    with LoggingContextManager(app_logger, "manage_expense_page"):
        app_logger.debug("Rendering Manage Expenses page")
        st.title("✏️ Manage Expenses")
        st.markdown("---")
        
        db = DatabaseManager()
        user_id = st.session_state.user['id']
        username = st.session_state.user['username']
        
        # Filters section
        with st.expander("📅 Date Filters", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                start_date = st.date_input(
                    "Start Date",
                    value=datetime.now().replace(day=1).date()
                )
            
            with col2:
                end_date = st.date_input(
                    "End Date",
                    value=datetime.now().date()
                )
                
        # Category filter
        category_filter = st.selectbox(
            "Filter by Category",
            ["All Categories"] + EXPENSE_CATEGORIES
        )
        
        # Get expenses
        try:
            expenses = db.get_user_expenses(user_id, start_date, end_date)
            app_logger.debug(f"Retrieved {len(expenses) if expenses else 0} expenses for user '{username}'")
            
            if not expenses:
                st.info("No expenses found for the selected date range.")
                return
            
            # Filter by category if needed
            filtered_expenses = []
            for expense in expenses:
                expense_id, amount, purpose, category, date, created_at = expense
                
                if category_filter == "All Categories" or category == category_filter:
                    filtered_expenses.append({
                        "ID": expense_id,
                        "Amount": amount,  # Keep as numeric for editing
                        "Display Amount": format_currency(amount),  # For display only
                        "Purpose": purpose,
                        "Category": category,
                        "Date": date,
                        "Created At": created_at
                    })
            
            if not filtered_expenses:
                st.info("No expenses found matching the selected filters.")
                return
            
            # Display as table with selection
            st.subheader("Select an expense to manage:")
            
            # Create a dictionary for showing in the table (without ID)
            display_expenses = []
            for idx, exp in enumerate(filtered_expenses):
                display_expenses.append({
                    "#": idx + 1,
                    "Date": exp["Date"],
                    "Amount": exp["Display Amount"],
                    "Purpose": exp["Purpose"],
                    "Category": exp["Category"]
                })
            
            # Show table with selection
            selected_index = st.selectbox(
                "Select an expense to manage:",
                options=range(len(display_expenses)),
                format_func=lambda i: f"{display_expenses[i]['#']} | {display_expenses[i]['Date']} | {display_expenses[i]['Amount']} | {display_expenses[i]['Purpose']} ({display_expenses[i]['Category']})"
            )
            
            # Get the selected expense
            selected_expense = filtered_expenses[selected_index]
            expense_id = selected_expense["ID"]
            
            st.markdown("---")
            st.subheader("Edit Expense")
            
            # Create tabs for managing the expense
            edit_tab, delete_tab = st.tabs(["✏️ Edit", "🗑️ Delete"])
            
            # Edit tab content
            with edit_tab:
                with st.form(key="edit_expense_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edit_amount = st.number_input(
                            "💰 Amount (₹)",
                            min_value=0.01,
                            max_value=1000000.0,
                            value=float(selected_expense["Amount"]),
                            step=10.0
                        )
                        
                        edit_purpose = st.text_input(
                            "📝 Purpose",
                            value=selected_expense["Purpose"]
                        )
                    
                    with col2:
                        # Find the index of the current category in the list
                        current_category_index = 0
                        for i, cat in enumerate(EXPENSE_CATEGORIES):
                            if cat == selected_expense["Category"]:
                                current_category_index = i
                                break
                        
                        edit_category = st.selectbox(
                            "🏷️ Category",
                            EXPENSE_CATEGORIES,
                            index=current_category_index
                        )
                        
                        # Convert the date string to a datetime.date object
                        if isinstance(selected_expense["Date"], str):
                            date_obj = datetime.strptime(selected_expense["Date"], "%Y-%m-%d").date()
                        else:
                            date_obj = selected_expense["Date"]
                        
                        edit_date = st.date_input(
                            "📅 Date",
                            value=date_obj,
                            max_value=datetime.now().date()
                        )
                    
                    submit_edit = st.form_submit_button("📝 Update Expense", use_container_width=True, type="primary")
                    
                    if submit_edit:
                        try:
                            app_logger.info(f"Updating expense ID={expense_id} for user '{username}'")
                            success = db.update_expense(
                                expense_id, 
                                edit_amount, 
                                edit_purpose.strip(), 
                                edit_category, 
                                edit_date
                            )
                            
                            if success:
                                st.success(f"✅ Successfully updated expense: {edit_purpose} ({format_currency(edit_amount)})")
                                # Force refresh of the page to show updated data
                                st.rerun()
                            else:
                                st.error("❌ Failed to update expense. No changes were made.")
                        except Exception as e:
                            app_logger.error(f"Error updating expense ID={expense_id}: {str(e)}")
                            st.error(f"❌ Error updating expense: {str(e)}")
            
            # Delete tab content
            with delete_tab:
                st.warning("⚠️ Are you sure you want to delete this expense? This action cannot be undone.")
                
                delete_col1, delete_col2 = st.columns([3, 1])
                
                with delete_col1:
                    st.info(f"""
                    **Expense Details:**
                    - Date: {selected_expense['Date']}
                    - Amount: {selected_expense['Display Amount']}
                    - Purpose: {selected_expense['Purpose']}
                    - Category: {selected_expense['Category']}
                    """)
                
                delete_confirmed = st.checkbox("I understand that this action is irreversible")
                
                if st.button("🗑️ Delete Expense", disabled=not delete_confirmed, type="primary", use_container_width=True):
                    try:
                        app_logger.info(f"Deleting expense ID={expense_id} for user '{username}'")
                        success = db.delete_expense(expense_id)
                        
                        if success:
                            st.success("✅ Expense successfully deleted")
                            # Force refresh of the page to show updated data
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete expense")
                    except Exception as e:
                        app_logger.error(f"Error deleting expense ID={expense_id}: {str(e)}")
                        st.error(f"❌ Error deleting expense: {str(e)}")
                        
        except Exception as e:
            app_logger.error(f"Error in manage_expenses page: {str(e)}")
            log_exception(app_logger, e, "manage_expenses page")
            st.error(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    # For testing - this code won't run when imported
    import streamlit as st
    st.set_page_config(page_title="Manage Expenses", page_icon="✏️", layout="wide")
    
    # Mock session state for testing
    if 'user' not in st.session_state:
        st.session_state.user = {'id': 1, 'username': 'test_user', 'full_name': 'Test User'}
    
    manage_expense_page()
