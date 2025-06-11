import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from database import DatabaseManager
from utils import format_currency, get_date_range_filter, create_expense_dataframe, get_spending_insights, display_metric_cards, style_dataframe

def dashboard_page():
    """Main dashboard page"""
    st.title(f"📊 Dashboard - {st.session_state.user['full_name']}")
    st.markdown("---")
    
    db = DatabaseManager()
    
    # Date range filter
    st.subheader("📅 Filter by Date Range")
    start_date, end_date = get_date_range_filter()
    
    # Get expenses data
    user_id = st.session_state.user['id']
    expenses = db.get_user_expenses(user_id, start_date, end_date)
    expenses_df = create_expense_dataframe(expenses)
    
    # Display metrics
    st.subheader("💰 Spending Overview")
    insights = get_spending_insights(expenses_df)
    display_metric_cards(insights)
    
    if not expenses_df.empty:
        # Charts section
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Spending by Category")
            category_data = expenses_df.groupby("Category")["Amount"].sum().reset_index()
            fig_pie = px.pie(
                category_data, 
                values="Amount", 
                names="Category",
                title="Category Distribution"
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            st.subheader("📊 Daily Spending Trend")
            daily_data = expenses_df.groupby("Date")["Amount"].sum().reset_index()
            fig_line = px.line(
                daily_data, 
                x="Date", 
                y="Amount",
                title="Daily Spending Pattern",
                markers=True
            )
            fig_line.update_layout(xaxis_title="Date", yaxis_title="Amount (₹)")
            st.plotly_chart(fig_line, use_container_width=True)
        
        # Category breakdown
        st.subheader("🏷️ Category Breakdown")
        category_summary = expenses_df.groupby("Category").agg({
            "Amount": ["sum", "count", "mean"]
        }).round(2)
        category_summary.columns = ["Total Spent", "Transactions", "Average"]
        category_summary["Total Spent"] = category_summary["Total Spent"].apply(format_currency)
        category_summary["Average"] = category_summary["Average"].apply(format_currency)
        category_summary = category_summary.sort_values("Transactions", ascending=False)
        st.dataframe(category_summary, use_container_width=True)
        
        # Recent transactions
        st.subheader("📝 Recent Transactions")
        recent_df = expenses_df.head(10).copy()
        recent_df = style_dataframe(recent_df)
        st.dataframe(recent_df, use_container_width=True, hide_index=True)
        
        # Monthly comparison
        st.subheader("📅 Monthly Comparison")
        monthly_data = db.get_monthly_summary(user_id)
        if monthly_data:
            monthly_df = pd.DataFrame(monthly_data, columns=["Month", "Amount"])
            fig_bar = px.bar(
                monthly_df, 
                x="Month", 
                y="Amount",
                title="Monthly Spending Comparison"
            )
            fig_bar.update_layout(xaxis_title="Month", yaxis_title="Amount (₹)")
            st.plotly_chart(fig_bar, use_container_width=True)
    
    else:
        st.info("No expenses found for the selected date range. Add some expenses to see your dashboard!")

def partner_dashboard():
    """Partner dashboard showing combined expenses"""
    st.title("👥 Partner Dashboard - Combined View")
    st.markdown("---")
    
    db = DatabaseManager()
    
    # Date range filter
    st.subheader("📅 Filter by Date Range")
    start_date, end_date = get_date_range_filter()
    
    # Get all expenses
    all_expenses = db.get_all_expenses(start_date, end_date)
    all_expenses_df = create_expense_dataframe(all_expenses, include_user=True)
    
    # Display combined metrics
    st.subheader("💰 Combined Spending Overview")
    insights = get_spending_insights(all_expenses_df)
    display_metric_cards(insights)
    
    if not all_expenses_df.empty:
        # User comparison
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("👤 Spending by User")
            user_data = all_expenses_df.groupby("User")["Amount"].sum().reset_index()
            fig_user = px.bar(
                user_data, 
                x="User", 
                y="Amount",
                title="Individual Spending Comparison",
                color="User"
            )
            fig_user.update_layout(xaxis_title="User", yaxis_title="Amount (₹)")
            st.plotly_chart(fig_user, use_container_width=True)
        
        with col2:
            st.subheader("📈 Combined Category Spending")
            category_data = all_expenses_df.groupby("Category")["Amount"].sum().reset_index()
            fig_pie = px.pie(
                category_data, 
                values="Amount", 
                names="Category",
                title="Combined Category Distribution"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Detailed breakdown by user and category
        st.subheader("🔍 Detailed Breakdown")
        user_category_data = all_expenses_df.groupby(["User", "Category"])["Amount"].sum().reset_index()
        fig_sunburst = px.sunburst(
            user_category_data, 
            path=["User", "Category"], 
            values="Amount",
            title="Spending Breakdown by User and Category"
        )
        st.plotly_chart(fig_sunburst, use_container_width=True)
        
        # Combined recent transactions
        st.subheader("📝 Recent Combined Transactions")
        recent_df = all_expenses_df.head(15).copy()
        recent_df = style_dataframe(recent_df)
        st.dataframe(recent_df, use_container_width=True, hide_index=True)
        
    else:
        st.info("No expenses found for the selected date range.")

def expense_analysis():
    """Advanced expense analysis"""
    st.title("🔍 Expense Analysis")
    st.markdown("---")
    
    db = DatabaseManager()
    user_id = st.session_state.user['id']
    
    # Analysis type selection
    analysis_type = st.radio(
        "Select Analysis Type:",
        ["Personal Analysis", "Comparative Analysis", "Trend Analysis"]
    )
    
    if analysis_type == "Personal Analysis":
        st.subheader("📊 Personal Spending Analysis")
        
        # Get user expenses for last 6 months
        six_months_ago = datetime.now() - timedelta(days=180)
        expenses = db.get_user_expenses(user_id, six_months_ago.date(), datetime.now().date())
        expenses_df = create_expense_dataframe(expenses)
        
        if not expenses_df.empty:
            # Spending patterns
            col1, col2 = st.columns(2)
            
            with col1:
                # Weekly spending pattern
                expenses_df['Weekday'] = pd.to_datetime(expenses_df['Date']).dt.day_name()
                weekday_spending = expenses_df.groupby('Weekday')['Amount'].sum().reindex([
                    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
                ])
                
                fig_weekday = px.bar(
                    x=weekday_spending.index,
                    y=weekday_spending.values,
                    title="Spending by Day of Week"
                )
                st.plotly_chart(fig_weekday, use_container_width=True)
            
            with col2:
                # Average transaction size by category
                avg_transaction = expenses_df.groupby('Category')['Amount'].mean().sort_values(ascending=False)
                fig_avg = px.bar(
                    x=avg_transaction.values,
                    y=avg_transaction.index,
                    orientation='h',
                    title="Average Transaction Size by Category"
                )
                st.plotly_chart(fig_avg, use_container_width=True)
    
    elif analysis_type == "Comparative Analysis":
        st.subheader("👥 Comparative Analysis")
        
        # Compare with other users
        all_expenses = db.get_all_expenses()
        all_expenses_df = create_expense_dataframe(all_expenses, include_user=True)
        
        if not all_expenses_df.empty:
            # Category spending comparison
            comparison_data = all_expenses_df.groupby(['User', 'Category'])['Amount'].sum().reset_index()
            fig_comparison = px.bar(
                comparison_data,
                x='Category',
                y='Amount',
                color='User',
                title="Category Spending Comparison",
                barmode='group'
            )
            fig_comparison.update_xaxes(tickangle=45)
            st.plotly_chart(fig_comparison, use_container_width=True)
            
            # Summary statistics
            st.subheader("📈 Summary Statistics")
            user_stats = all_expenses_df.groupby('User')['Amount'].agg(['sum', 'mean', 'count']).round(2)
            user_stats.columns = ['Total Spent', 'Average Transaction', 'Total Transactions']
            user_stats['Total Spent'] = user_stats['Total Spent'].apply(format_currency)
            user_stats['Average Transaction'] = user_stats['Average Transaction'].apply(format_currency)
            st.dataframe(user_stats, use_container_width=True)
    
    else:  # Trend Analysis
        st.subheader("📈 Trend Analysis")
        
        # Monthly trends
        monthly_data = db.get_monthly_summary(user_id)
        if monthly_data:
            monthly_df = pd.DataFrame(monthly_data, columns=["Month", "Amount"])
            monthly_df['Month'] = pd.to_datetime(monthly_df['Month'])
            
            # Calculate trend
            monthly_df['Trend'] = monthly_df['Amount'].pct_change() * 100
            
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=monthly_df['Month'],
                y=monthly_df['Amount'],
                mode='lines+markers',
                name='Monthly Spending',
                line=dict(color='blue', width=3)
            ))
            
            fig_trend.update_layout(
                title='Monthly Spending Trend',
                xaxis_title='Month',
                yaxis_title='Amount (₹)',
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # Trend insights
            latest_trend = monthly_df['Trend'].iloc[-1] if len(monthly_df) > 1 else 0
            if latest_trend > 0:
                st.success(f"📈 Your spending increased by {latest_trend:.1f}% compared to last month")
            elif latest_trend < 0:
                st.success(f"📉 Your spending decreased by {abs(latest_trend):.1f}% compared to last month")
            else:
                st.info("📊 Your spending remained stable compared to last month")