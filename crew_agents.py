__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import streamlit as st
import pandas as pd
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from database import DatabaseManager
from utils import create_expense_dataframe, format_currency
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
os.environ["AZURE_API_KEY"] = st.secrets.get("AZURE_API_KEY")
os.environ["AZURE_API_BASE"] = st.secrets.get("AZURE_API_BASE")
os.environ["AZURE_API_VERSION"] = st.secrets.get("AZURE_API_VERSION")
llm = LLM(
    model="azure/gpt-4.1-mini",
    api_version="2025-01-01-preview"
)
@tool
def get_user_expenses_data(user_id: int, days_back: int = 30) -> str:
    """Get user expense data for analysis"""
    db = DatabaseManager()
    start_date = datetime.now() - timedelta(days=days_back)
    expenses = db.get_user_expenses(user_id, start_date.date(), datetime.now().date())
    
    if not expenses:
        return "No expenses found for the specified period."
    
    df = create_expense_dataframe(expenses)
    
    # Create summary
    total_spent = df['Amount'].sum()
    avg_daily = total_spent / days_back
    top_category = df.groupby('Category')['Amount'].sum().idxmax()
    transaction_count = len(df)
    
    category_breakdown = df.groupby('Category')['Amount'].sum().to_dict()
    
    summary = f"""
    Expense Summary for last {days_back} days:
    - Total Spent: {format_currency(total_spent)}
    - Average Daily Spending: {format_currency(avg_daily)}
    - Total Transactions: {transaction_count}
    - Top Spending Category: {top_category}
    
    Category Breakdown:
    """
    
    for category, amount in category_breakdown.items():
        summary += f"- {category}: {format_currency(amount)}\n"
    
    return summary

@tool
def get_category_insights(user_id: int, category: str = None) -> str:
    """Get insights about spending in specific categories"""
    db = DatabaseManager()
    expenses = db.get_user_expenses(user_id)
    
    if not expenses:
        return "No expenses found."
    
    df = create_expense_dataframe(expenses)
    
    if category:
        category_data = df[df['Category'].str.contains(category, case=False, na=False)]
        if category_data.empty:
            return f"No expenses found for category containing '{category}'"
        
        total_spent = category_data['Amount'].sum()
        avg_transaction = category_data['Amount'].mean()
        transaction_count = len(category_data)
        
        return f"""
        Insights for {category} category:
        - Total Spent: {format_currency(total_spent)}
        - Average Transaction: {format_currency(avg_transaction)}
        - Number of Transactions: {transaction_count}
        - Percentage of Total Spending: {(total_spent / df['Amount'].sum() * 100):.1f}%
        """
    else:
        category_summary = df.groupby('Category')['Amount'].agg(['sum', 'count', 'mean']).round(2)
        
        insights = "Category Insights:\n"
        for category, data in category_summary.iterrows():
            insights += f"- {category}: Total: {format_currency(data['sum'])}, "
            insights += f"Transactions: {data['count']}, Average: {format_currency(data['mean'])}\n"
        
        return insights

@tool
def get_spending_trends(user_id: int) -> str:
    """Analyze spending trends over time"""
    db = DatabaseManager()
    monthly_data = db.get_monthly_summary(user_id)
    
    if not monthly_data or len(monthly_data) < 2:
        return "Insufficient data to analyze trends."
    
    df = pd.DataFrame(monthly_data, columns=['Month', 'Amount'])
    df = df.sort_values('Month')
    
    # Calculate trends
    latest_month = df.iloc[-1]['Amount']
    previous_month = df.iloc[-2]['Amount']
    trend_pct = ((latest_month - previous_month) / previous_month) * 100
    
    avg_monthly = df['Amount'].mean()
    highest_month = df.loc[df['Amount'].idxmax()]
    lowest_month = df.loc[df['Amount'].idxmin()]
    
    trend_analysis = f"""
    Spending Trend Analysis:
    - Latest Month Spending: {format_currency(latest_month)}
    - Previous Month Spending: {format_currency(previous_month)}
    - Month-over-Month Change: {trend_pct:+.1f}%
    - Average Monthly Spending: {format_currency(avg_monthly)}
    - Highest Spending Month: {highest_month['Month']} ({format_currency(highest_month['Amount'])})
    - Lowest Spending Month: {lowest_month['Month']} ({format_currency(lowest_month['Amount'])})
    
    Trend Direction: {"Increasing" if trend_pct > 0 else "Decreasing" if trend_pct < 0 else "Stable"}
    """
    
    return trend_analysis

@tool
def compare_with_budget(user_id: int, monthly_budget: float) -> str:
    """Compare spending with a given budget"""
    db = DatabaseManager()
    current_month_start = datetime.now().replace(day=1).date()
    expenses = db.get_user_expenses(user_id, current_month_start, datetime.now().date())
    
    if not expenses:
        return "No expenses found for current month."
    
    df = create_expense_dataframe(expenses)
    current_spending = df['Amount'].sum()
    
    days_passed = (datetime.now().date() - current_month_start).days + 1
    days_in_month = 30  # Approximate
    projected_spending = (current_spending / days_passed) * days_in_month
    
    budget_analysis = f"""
    Budget Analysis:
    - Monthly Budget: {format_currency(monthly_budget)}
    - Current Month Spending: {format_currency(current_spending)}
    - Projected Month Spending: {format_currency(projected_spending)}
    - Budget Remaining: {format_currency(monthly_budget - current_spending)}
    - Budget Usage: {(current_spending / monthly_budget * 100):.1f}%
    
    Status: {"Over Budget" if projected_spending > monthly_budget else "On Track" if projected_spending <= monthly_budget * 0.9 else "Close to Budget Limit"}
    """
    
    return budget_analysis

class ExpenseAdvisorCrew:
    def __init__(self):
        # Initialize agents
        self.financial_analyst = Agent(
            role='Financial Analyst',
            goal='Analyze spending patterns and provide financial insights',
            backstory="""You are an expert financial analyst specializing in personal finance. 
            You analyze spending patterns, identify trends, and provide actionable insights 
            to help people manage their money better.""",
            verbose=True,
            allow_delegation=False,
            tools=[get_user_expenses_data, get_category_insights, get_spending_trends],
            llm=llm
        )
        
        self.budget_advisor = Agent(
            role='Budget Advisor',
            goal='Provide budgeting advice and spending recommendations',
            backstory="""You are a certified financial planner who specializes in budgeting 
            and expense management. You help people create realistic budgets and stick to them.""",
            verbose=True,
            allow_delegation=False,
            tools=[compare_with_budget, get_user_expenses_data],
            llm=llm
        )
        
        self.savings_expert = Agent(
            role='Savings Expert',
            goal='Identify savings opportunities and provide money-saving tips',
            backstory="""You are a personal finance expert focused on helping people save money. 
            You analyze spending patterns to identify areas where expenses can be reduced.""",
            verbose=True,
            allow_delegation=False,
            tools=[get_category_insights, get_spending_trends],
            llm=llm
        )
    
    def analyze_spending_patterns(self, user_id: int) -> str:
        """Analyze user's spending patterns"""
        task = Task(
            description=f"""Analyze the spending patterns for user ID {user_id}. 
            Look at the last 30 days of expenses and provide insights about:
            1. Overall spending behavior
            2. Top spending categories
            3. Any concerning patterns
            4. Recommendations for improvement""",
            agent=self.financial_analyst,
            expected_output="A detailed analysis of spending patterns with actionable insights"
        )
        
        crew = Crew(
            agents=[self.financial_analyst],
            tasks=[task],
            verbose=True,
            process=Process.sequential
        )
        
        try:
            result = crew.kickoff()
            return str(result)
        except Exception as e:
            return f"Analysis unavailable: {str(e)}"
    
    def get_budget_advice(self, user_id: int, monthly_budget: float) -> str:
        """Get budget advice based on spending"""
        task = Task(
            description=f"""Provide budget advice for user ID {user_id} with a monthly budget of {monthly_budget}. 
            Analyze current spending against the budget and provide:
            1. Budget performance assessment
            2. Areas where spending can be optimized
            3. Specific recommendations to stay within budget
            4. Warning signs to watch for""",
            agent=self.budget_advisor,
            expected_output="Comprehensive budget advice with practical recommendations"
        )
        
        crew = Crew(
            agents=[self.budget_advisor],
            tasks=[task],
            verbose=True,
            process=Process.sequential
        )
        
        try:
            result = crew.kickoff()
            return str(result)
        except Exception as e:
            return f"Budget advice unavailable: {str(e)}"
    
    def find_savings_opportunities(self, user_id: int) -> str:
        """Find opportunities to save money"""
        task = Task(
            description=f"""Identify money-saving opportunities for user ID {user_id}. 
            Analyze spending patterns and suggest:
            1. Categories where spending can be reduced
            2. Specific cost-cutting strategies
            3. Alternative approaches to expensive habits
            4. Long-term savings strategies""",
            agent=self.savings_expert,
            expected_output="Actionable money-saving recommendations"
        )
        
        crew = Crew(
            agents=[self.savings_expert],
            tasks=[task],
            verbose=True,
            process=Process.sequential
        )
        
        try:
            result = crew.kickoff()
            return str(result)
        except Exception as e:
            return f"Savings advice unavailable: {str(e)}"

def ai_assistant_page():
    """AI Assistant page with CrewAI agents"""
    st.title("🤖 AI Financial Assistant")
    st.markdown("Get personalized financial insights powered by AI agents")
    st.markdown("---")

    
    crew = ExpenseAdvisorCrew()
    user_id = st.session_state.user['id']
    
    # Analysis type selection
    analysis_type = st.selectbox(
        "What would you like to analyze?",
        [
            "💡 Spending Pattern Analysis",
            "💰 Budget Planning Advice", 
            "💸 Savings Opportunities"
        ]
    )
    
    if analysis_type == "💡 Spending Pattern Analysis":
        st.subheader("📊 Spending Pattern Analysis")
        
        if st.button("Analyze My Spending Patterns", type="primary"):
            with st.spinner("🔍 Analyzing your spending patterns..."):
                result = crew.analyze_spending_patterns(user_id)
                st.success("Analysis Complete!")
                st.markdown(result)
    
    elif analysis_type == "💰 Budget Planning Advice":
        st.subheader("📋 Budget Planning Advice")
        
        monthly_budget = st.number_input(
            "Enter your monthly budget (₹):",
            min_value=1000,
            max_value=1000000,
            value=50000,
            step=1000
        )
        
        if st.button("Get Budget Advice", type="primary"):
            with st.spinner("💡 Generating personalized budget advice..."):
                result = crew.get_budget_advice(user_id, monthly_budget)
                st.success("Advice Ready!")
                st.markdown(result)
    
    else:  # Savings Opportunities
        st.subheader("💸 Savings Opportunities")
        
        if st.button("Find Savings Opportunities", type="primary"):
            with st.spinner("🔎 Identifying money-saving opportunities..."):
                result = crew.find_savings_opportunities(user_id)
                st.success("Opportunities Identified!")
                st.markdown(result)
    
    # Quick insights section
    st.markdown("---")
    st.subheader("⚡ Quick Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📈 Spending Trends"):
            with st.spinner("Analyzing trends..."):
                db = DatabaseManager()
                monthly_data = db.get_monthly_summary(user_id)
                if monthly_data and len(monthly_data) >= 2:
                    latest = monthly_data[0][1]  # Most recent month
                    previous = monthly_data[1][1] if len(monthly_data) > 1 else latest
                    change = ((latest - previous) / previous) * 100 if previous > 0 else 0
                    
                    if change > 10:
                        st.warning(f"📈 Spending increased by {change:.1f}% compared to last month")
                    elif change < -10:
                        st.success(f"📉 Spending decreased by {abs(change):.1f}% compared to last month")
                    else:
                        st.info(f"📊 Spending is relatively stable ({change:+.1f}% change)")
                else:
                    st.info("Need more data to analyze trends")
    
    with col2:
        if st.button("🏷️ Top Categories"):
            with st.spinner("Analyzing categories..."):
                db = DatabaseManager()
                category_data = db.get_category_summary(user_id)
                if category_data:
                    top_category = category_data[0]
                    st.info(f"🥇 Top category: **{top_category[0]}** \n💰 Total: {format_currency(top_category[1])}")
                else:
                    st.info("No spending data available")
