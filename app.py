import streamlit as st
from datetime import datetime
from auth import init_session_state, login_page, logout, require_auth
from database import DatabaseManager
from dashboard import dashboard_page, partner_dashboard, expense_analysis
from manage_expenses import manage_expense_page
from user_management import user_management_page
from crew_agents import ai_assistant_page
from utils import EXPENSE_CATEGORIES, format_currency
from logger import app_logger, LoggingContextManager, log_exception

# Page configuration
st.set_page_config(
    page_title="Personal Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        color: #1f77b4;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .expense-form {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

def add_expense_page():
    """Add expense page"""
    with LoggingContextManager(app_logger, "add_expense_page"):
        app_logger.debug("Rendering Add Expense page")
        st.title("➕ Add New Expense")
        st.markdown("---")
        
        db = DatabaseManager()
        
        with st.form("expense_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                amount = st.number_input(
                    "💰 Amount (₹)",
                    min_value=0.01,
                    max_value=1000000.0,
                    value=100.0,
                    step=10.0,
                    help="Enter the expense amount"
                )
                
                purpose = st.text_input(
                    "📝 Purpose",
                    placeholder="e.g., Lunch at restaurant, Monthly groceries",
                    help="Brief description of the expense"
                )
            
            with col2:
                category = st.selectbox(
                    "🏷️ Category",
                    EXPENSE_CATEGORIES,
                    help="Select the expense category"
                )
                
                expense_date = st.date_input(
                    "📅 Date",
                    value=datetime.now().date(),
                    max_value=datetime.now().date(),
                    help="Date of the expense"
                )
            
            submitted = st.form_submit_button("💾 Add Expense", type="primary", use_container_width=True)
            
            if submitted:
                app_logger.info(f"Expense form submitted: amount={amount}, purpose='{purpose}', category='{category}'")
                if amount > 0 and purpose.strip():
                    try:
                        user_id = st.session_state.user['id']
                        username = st.session_state.user['username']
                        db.add_expense(user_id, amount, purpose.strip(), category, expense_date)
                        app_logger.info(f"User '{username}' added expense: amount={amount}, purpose='{purpose}', category='{category}'")
                        st.success(f"✅ Successfully added expense of {format_currency(amount)} for {purpose}")
                        st.balloons()
                    except Exception as e:
                        app_logger.error(f"Error adding expense: {str(e)}")
                        st.error(f"❌ Error adding expense: {str(e)}")
                else:
                    app_logger.warning(f"Invalid form submission: amount={amount}, purpose='{purpose}'")
                    st.error("❌ Please enter a valid amount and purpose")

def view_expenses_page():
    """View expenses page"""
    st.title("📋 My Expenses")
    st.markdown("---")
    
    db = DatabaseManager()
    user_id = st.session_state.user['id']
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
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
    
    with col3:
        category_filter = st.selectbox(
            "Filter by Category",
            ["All Categories"] + EXPENSE_CATEGORIES
        )
    
    # Get expenses
    expenses = db.get_user_expenses(user_id, start_date, end_date)
    
    if expenses:
        # Convert to display format
        expense_data = []
        total_amount = 0
        
        for expense in expenses:
            expense_id, amount, purpose, category, date, created_at = expense
            
            # Apply category filter
            if category_filter != "All Categories" and category != category_filter:
                continue
            
            expense_data.append({
                "Date": date,
                "Amount": format_currency(amount),
                "Purpose": purpose,
                "Category": category,
                "ID": expense_id
            })
            total_amount += amount
        
        if expense_data:
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Expenses", format_currency(total_amount))
            
            with col2:
                st.metric("Number of Transactions", len(expense_data))
            
            with col3:
                avg_amount = total_amount / len(expense_data)
                st.metric("Average Amount", format_currency(avg_amount))
            
            st.markdown("---")
            
            # Expenses table
            st.subheader("📊 Expense Details")
            
            # Display expenses (excluding ID column)
            display_data = [{k: v for k, v in exp.items() if k != "ID"} for exp in expense_data]
            st.dataframe(
                display_data,
                use_container_width=True,
                hide_index=True
            )
            
            # Export functionality
            if st.button("📥 Export to CSV"):
                import pandas as pd
                df = pd.DataFrame(display_data)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"expenses_{start_date}_{end_date}.csv",
                    mime="text/csv"
                )
        else:
            st.info("No expenses found matching the selected filters.")
    else:
        st.info("No expenses found for the selected date range.")

@require_auth
def main_app():
    """Main application interface"""
    with LoggingContextManager(app_logger, "main_app"):
        username = st.session_state.user['username']
        app_logger.info(f"Loading main application for user '{username}'")
        
        # Sidebar navigation
        st.sidebar.title(f"👋 Welcome, {st.session_state.user['full_name']}")
        st.sidebar.markdown("---")          # Navigation menu
        pages = {
            "📊 Dashboard": dashboard_page,
            "➕ Add Expense": add_expense_page,
            "📋 View Expenses": view_expenses_page,
            "✏️ Manage Expenses": manage_expense_page,
            "🔍 Analysis": expense_analysis,
            "🤖 AI Assistant": ai_assistant_page
        }
        
        # Add user management for admin users
        if st.session_state.user['username'] in ['admin', 'sana']:
            pages["👤 User Management"] = user_management_page
    
    # Add partner dashboard for specific user
    if st.session_state.user['username'] in ['partner', 'user1']:
        pages["👥 Partner Dashboard"] = partner_dashboard
    
    selected_page = st.sidebar.radio("Navigate to:", list(pages.keys()))
    
    # User info and logout
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**User:** {st.session_state.user['username']}")
    st.sidebar.markdown(f"**Name:** {st.session_state.user['full_name']}")
    
    if st.sidebar.button("🚪 Logout", type="secondary"):
        logout()
    
    # Quick stats in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Quick Stats")
    
    db = DatabaseManager()
    user_id = st.session_state.user['id']
    
    # Current month expenses
    current_month_start = datetime.now().replace(day=1).date()
    current_expenses = db.get_user_expenses(user_id, current_month_start, datetime.now().date())
    
    if current_expenses:
        total_current = sum(exp[1] for exp in current_expenses)
        st.sidebar.metric("This Month", format_currency(total_current))
    else:
        st.sidebar.metric("This Month", "₹0.00")
    
    # Top category this month
    if current_expenses:
        from utils import create_expense_dataframe
        df = create_expense_dataframe(current_expenses)
        if not df.empty:
            top_category = df.groupby('Category')['Amount'].sum().idxmax()
            top_amount = df.groupby('Category')['Amount'].sum().max()
            st.sidebar.markdown(f"**Top Category:** {top_category.split(' ', 1)[1] if ' ' in top_category else top_category}")
            st.sidebar.markdown(f"**Amount:** {format_currency(top_amount)}")
    
    # Display selected page
    pages[selected_page]()

def main():
    """Main function"""
    with LoggingContextManager(app_logger, "main"):
        app_logger.info("Application started")
        try:
            init_session_state()
            
            if not st.session_state.authenticated:
                app_logger.debug("User not authenticated, showing login page")
                login_page()
            else:
                app_logger.debug("User authenticated, loading main application")
                main_app()
        except Exception as e:
            app_logger.error(f"Unhandled error in main function: {str(e)}")
            log_exception(app_logger, e, "main application")
            st.error("An unexpected error occurred. Please try refreshing the page.")

if __name__ == "__main__":
    try:
        app_logger.info("Starting Expense Tracker application")
        main()
    except Exception as e:
        app_logger.critical(f"Critical application error: {str(e)}")
        log_exception(app_logger, e, "application startup")