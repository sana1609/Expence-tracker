import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# Predefined categories
EXPENSE_CATEGORIES = [
    "🍔 Food & Dining",
    "🚗 Transportation", 
    "🏠 Housing & Utilities",
    "🛒 Groceries",
    "💊 Healthcare",
    "🎬 Entertainment",
    "👕 Clothing",
    "📚 Education",
    "🎁 Gifts",
    "💰 Savings & Investment",
    "🔧 Maintenance",
    "☎️ Communication",
    "✈️ Travel",
    "🏋️ Fitness",
    "📱 Technology"
]

def format_currency(amount):
    """Format amount as currency"""
    return f"₹{amount:,.2f}"

def get_date_range_filter():
    """Get date range filter widget"""
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=30),
            max_value=datetime.now().date()
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now().date(),
            max_value=datetime.now().date()
        )
    
    return start_date, end_date

def create_expense_dataframe(expenses, include_user=False):
    """Convert expense data to pandas DataFrame"""
    if not expenses:
        columns = ["Amount", "Purpose", "Category", "Date"]
        if include_user:
            columns.append("User")
        return pd.DataFrame(columns=columns)
    
    if include_user:
        df = pd.DataFrame(expenses, columns=["ID", "Amount", "Purpose", "Category", "Date", "User"])
    else:
        df = pd.DataFrame(expenses, columns=["ID", "Amount", "Purpose", "Category", "Date", "Created"])
        df = df.drop(["ID", "Created"], axis=1)
    
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    df["Amount"] = df["Amount"].astype(float)
    
    return df

def get_spending_insights(expenses_df):
    """Generate spending insights"""
    if expenses_df.empty:
        return {
            "total_spent": 0,
            "avg_daily": 0,
            "top_category": "None",
            "transaction_count": 0
        }
    
    total_spent = expenses_df["Amount"].sum()
    avg_daily = total_spent / 30  # Assuming 30-day period
    top_category = expenses_df.groupby("Category")["Amount"].sum().idxmax()
    transaction_count = len(expenses_df)
    
    return {
        "total_spent": total_spent,
        "avg_daily": avg_daily,
        "top_category": top_category,
        "transaction_count": transaction_count
    }

def display_metric_cards(insights):
    """Display metric cards"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Spent",
            format_currency(insights["total_spent"]),
            delta=f"{insights['transaction_count']} transactions"
        )
    
    with col2:
        st.metric(
            "Daily Average",
            format_currency(insights["avg_daily"]),
        )
    
    with col3:
        st.metric(
            "Top Category",
            insights["top_category"].replace("🎯 ", "") if insights["top_category"] != "None" else "None"
        )
    
    with col4:
        st.metric(
            "Transactions",
            insights["transaction_count"]
        )

def style_dataframe(df):
    """Apply styling to dataframe"""
    if df.empty:
        return df
    
    # Format amount column
    if "Amount" in df.columns:
        df["Amount"] = df["Amount"].apply(format_currency)
    
    return df