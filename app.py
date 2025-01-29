import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime

def main():
    st.title("Personal Finance Manager 💰")

    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = "default_user"
    if 'transactions' not in st.session_state:
        st.session_state.transactions = load_from_database()
    if 'savings_goal' not in st.session_state:
        st.session_state.savings_goal = load_savings_goal_from_database()

    # Sidebar navigation
    page = st.sidebar.selectbox("Navigate", ["Dashboard", "Transactions", "Budget Management", "Savings Goals", "Automated Payments", "Loans", "Data Export"])

    if page == "Dashboard":
        show_dashboard()
    elif page == "Transactions":
        show_transactions()
    elif page == "Budget Management":
        budget_management()
    elif page == "Savings Goals":
        savings_goals()
    elif page == "Automated Payments":
        automated_payments()
    elif page == "Loans":
        loans()
    elif page == "Data Export":
        data_export()

def show_dashboard():
    st.header("Financial Dashboard")
    
    if st.session_state.transactions.empty:
        st.warning("No transactions available. Please add transactions or upload a CSV file.")
        return

    # Key Metrics
    total_income = st.session_state.transactions[st.session_state.transactions['Type'] == 'Income']['Amount'].sum()
    total_expenses = st.session_state.transactions[st.session_state.transactions['Type'] == 'Expense']['Amount'].sum()
    net_savings = total_income - total_expenses

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"${total_income:.2f}")
    col2.metric("Total Expenses", f"${total_expenses:.2f}")
    col3.metric("Net Savings", f"${net_savings:.2f}")

    # Monthly Summary
    st.subheader("Monthly Summary")
    monthly_data = st.session_state.transactions.copy()
    monthly_data['Date'] = pd.to_datetime(monthly_data['Date'])
    monthly_data['Month'] = monthly_data['Date'].dt.to_period('M').astype(str)
    monthly_summary = monthly_data.groupby(['Month', 'Type'])['Amount'].sum().unstack(fill_value=0).reindex(columns=['Income', 'Expense'], fill_value=0)
    
    monthly_summary['Net'] = monthly_summary['Income'] - monthly_summary['Expense']
    monthly_summary = monthly_summary.reset_index()
    fig_monthly = px.bar(monthly_summary, x='Month', y=['Income', 'Expense', 'Net'],
                         title='Monthly Income, Expenses, and Net Savings',
                         labels={'value': 'Amount', 'variable': 'Type'})
    st.plotly_chart(fig_monthly)

    # Expense Breakdown Pie Chart
    st.subheader("Expense Breakdown")
    expense_data = st.session_state.transactions[st.session_state.transactions['Type'] == 'Expense']
    if not expense_data.empty:
        fig_pie = px.pie(expense_data, values='Amount', names='Category', title='Expense Breakdown')
        st.plotly_chart(fig_pie)
    else:
        st.info("No expenses to display.")

def show_transactions():
    st.header("Transactions")
    
    # Add new transaction
    st.subheader("Add New Transaction")
    date = st.date_input("Date", datetime.now().date())
    category = st.selectbox("Category", ["Food & Groceries", "Transportation", "Housing/Rent", "Utilities", "Entertainment", "Shopping", "Healthcare", "Salary", "Other"])
    amount = st.number_input("Amount", min_value=0.01, format="%.2f")
    description = st.text_input("Description")
    transaction_type = st.selectbox("Type", ["Income", "Expense"])

    if st.button("Add Transaction"):
        new_transaction = pd.DataFrame({
            'Date': [date],
            'Category': [category],
            'Amount': [amount],
            'Description': [description],
            'Type': [transaction_type],
            'User': [st.session_state.user]
        })
        save_to_database(new_transaction)
        st.session_state.transactions = load_from_database()
        st.success("Transaction added successfully!")
        st.rerun()

    # Display transaction history
    st.subheader("Transaction History")
    if not st.session_state.transactions.empty:
        st.dataframe(st.session_state.transactions.sort_values('Date', ascending=False))
    else:
        st.info("No transactions available.")

def budget_management():
    st.header("Budget Management")
    
    # Load budget data from database
    budget_data = load_budget_from_database()
    
    # Simple budget allocation
    st.subheader("Set Budget Allocations")
    categories = ["Food & Groceries", "Transportation", "Housing/Rent", "Utilities", "Entertainment", "Shopping", "Healthcare", "Other"]
    new_budget_data = {}
    
    for category in categories:
        current_budget = float(budget_data.get(category, 0.0))  # Ensure default is a float
        new_budget_data[category] = st.number_input(f"Budget for {category}", min_value=0.0, value=current_budget, format="%.2f")
    
    if st.button("Save Budget"):
        save_budget_to_database(new_budget_data)
        st.success("Budget saved successfully!")
    
    # Budget comparison
    st.subheader("Budget vs Actual Spending")
    actual_spending = st.session_state.transactions[st.session_state.transactions['Type'] == 'Expense'].groupby('Category')['Amount'].sum()
    
    comparison_data = []
    for category, budget in new_budget_data.items():
        actual = actual_spending.get(category, 0)
        comparison_data.append({
            'Category': category,
            'Budget': budget,
            'Actual': actual,
            'Difference': budget - actual
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    fig_comparison = go.Figure(data=[
        go.Bar(name='Budget', x=comparison_df['Category'], y=comparison_df['Budget']),
        go.Bar(name='Actual', x=comparison_df['Category'], y=comparison_df['Actual'])
    ])
    fig_comparison.update_layout(title='Budget vs Actual Spending', barmode='group')
    st.plotly_chart(fig_comparison)
    
    # Alerts
    st.subheader("Budget Alerts")
    for _, row in comparison_df.iterrows():
        if row['Actual'] > row['Budget']:
            st.warning(f"Overspending in {row['Category']}: Budget ${row['Budget']:.2f}, Actual ${row['Actual']:.2f}")

def savings_goals():
    st.header("Savings Goals")
    
    current_goal = float(st.session_state.savings_goal)  # Ensure it's a float
    new_goal = st.number_input("Set your savings goal", min_value=0.0, value=current_goal, format="%.2f")
    
    if st.button("Update Savings Goal"):
        st.session_state.savings_goal = new_goal
        save_savings_goal_to_database(new_goal)
        st.success("Savings goal updated successfully!")
    
    # Calculate total savings
    total_income = st.session_state.transactions[st.session_state.transactions['Type'] == 'Income']['Amount'].sum()
    total_expenses = st.session_state.transactions[st.session_state.transactions['Type'] == 'Expense']['Amount'].sum()
    total_savings = total_income - total_expenses

    # Load automated payments and calculate expected expenses
    automated_payments = load_automated_payments_from_database()
    expected_expenses = automated_payments['Amount'].sum() if not automated_payments.empty else 0

    # Adjust total savings by subtracting expected expenses
    adjusted_savings = total_savings - expected_expenses

    # Calculate progress as a fraction
    progress = (adjusted_savings / new_goal) if new_goal > 0 else 0
    progress = max(0, min(progress, 1))  # Ensure progress is between 0 and 1
    
    st.progress(progress)
    st.write(f"Current savings: ${adjusted_savings:.2f}")
    st.write(f"Progress towards goal: {progress * 100:.1f}%")

def automated_payments():
    st.header("Automated Payments")
    
    # Add new automated payment
    st.subheader("Add New Automated Payment")
    payment_name = st.text_input("Payment Name")
    amount = st.number_input("Amount", min_value=0.01, format="%.2f")
    frequency = st.selectbox("Frequency", ["Weekly", "Monthly", "Yearly"])
    next_payment_date = st.date_input("Next Payment Date", datetime.now().date())

    if st.button("Add Automated Payment"):
        new_payment = pd.DataFrame({
            'Name': [payment_name],
            'Amount': [amount],
            'Frequency': [frequency],
            'NextPaymentDate': [next_payment_date],
            'User': [st.session_state.user]
        })
        save_automated_payment_to_database(new_payment)
        st.success("Automated payment added successfully!")

    # Display automated payments
    st.subheader("Automated Payments List")
    payments = load_automated_payments_from_database()
    if not payments.empty:
        st.dataframe(payments)
    else:
        st.info("No automated payments available.")

def loans():
    st.header("Loans Management")
    
    # Add new loan
    st.subheader("Add New Loan")
    loan_name = st.text_input("Loan Name")
    amount = st.number_input("Loan Amount", min_value=0.01, format="%.2f")
    loan_type = st.selectbox("Loan Type", ["Given", "Taken"])
    due_date = st.date_input("Due Date", datetime.now().date())

    if st.button("Add Loan"):
        new_loan = pd.DataFrame({
            'Name': [loan_name],
            'Amount': [amount],
            'Type': [loan_type],
            'DueDate': [due_date],
            'User': [st.session_state.user]
        })
        save_loan_to_database(new_loan)
        st.success("Loan added successfully!")

        # If the loan is given, add it as an "Other Expense" transaction
        if loan_type == "Given":
            new_transaction = pd.DataFrame({
                'Date': [datetime.now().date()],
                'Category': ["Other"],
                'Amount': [amount],
                'Description': [f"Loan Given: {loan_name}"],
                'Type': ["Expense"],
                'User': [st.session_state.user]
            })
            save_to_database(new_transaction)
            st.session_state.transactions = load_from_database()
            st.success("Loan recorded as an expense in transactions!")

    # Display loans
    st.subheader("Loans List")
    loans = load_loans_from_database()
    if not loans.empty:
        st.dataframe(loans)
    else:
        st.info("No loans available.")

def data_export():
    st.header("Export Data")
    
    if st.button("Export to CSV"):
        csv = st.session_state.transactions.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="personal_finance_data.csv",
            mime="text/csv"
        )

def save_to_database(df):
    try:
        conn = sqlite3.connect('finance_data.db')
        df.to_sql('transactions', conn, if_exists='append', index=False)
        conn.close()
    except sqlite3.Error as e:
        st.error(f"An error occurred while saving to the database: {e}")

def load_from_database():
    try:
        conn = sqlite3.connect('finance_data.db')
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions
        (Date TEXT, Category TEXT, Amount REAL, Description TEXT, Type TEXT, User TEXT)
        ''')
        
        df = pd.read_sql('SELECT * FROM transactions', conn)
        conn.close()
        return df
    except sqlite3.Error as e:
        st.error(f"An error occurred while loading from the database: {e}")
        return pd.DataFrame()

def save_budget_to_database(budget_data):
    try:
        conn = sqlite3.connect('finance_data.db')
        cursor = conn.cursor()
        
        # Create budget table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS budget
        (Category TEXT PRIMARY KEY, Amount REAL)
        ''')
        
        # Insert or update budget data
        for category, amount in budget_data.items():
            cursor.execute('INSERT OR REPLACE INTO budget (Category, Amount) VALUES (?, ?)', (category, amount))
        
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        st.error(f"An error occurred while saving the budget: {e}")

def load_budget_from_database():
    try:
        conn = sqlite3.connect('finance_data.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM budget')
        budget_data = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        return budget_data
    except sqlite3.Error as e:
        st.error(f"An error occurred while loading the budget: {e}")
        return {}

def save_savings_goal_to_database(goal):
    try:
        conn = sqlite3.connect('finance_data.db')
        cursor = conn.cursor()
        
        # Create savings_goal table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS savings_goal
        (User TEXT PRIMARY KEY, Goal REAL)
        ''')
        
        # Insert or update savings goal
        cursor.execute('INSERT OR REPLACE INTO savings_goal (User, Goal) VALUES (?, ?)', (st.session_state.user, goal))
        
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        st.error(f"An error occurred while saving the savings goal: {e}")

def load_savings_goal_from_database():
    try:
        conn = sqlite3.connect('finance_data.db')
        cursor = conn.cursor()
        
        # Create savings_goal table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS savings_goal
        (User TEXT PRIMARY KEY, Goal REAL)
        ''')
        
        cursor.execute('SELECT Goal FROM savings_goal WHERE User = ?', (st.session_state.user,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else 0
    except sqlite3.Error as e:
        st.error(f"An error occurred while loading the savings goal: {e}")
        return 0

def save_automated_payment_to_database(df):
    try:
        conn = sqlite3.connect('finance_data.db')
        cursor = conn.cursor()
        
        # Create automated_payments table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS automated_payments
        (Name TEXT, Amount REAL, Frequency TEXT, NextPaymentDate TEXT, User TEXT)
        ''')
        
        df.to_sql('automated_payments', conn, if_exists='append', index=False)
        conn.close()
    except sqlite3.Error as e:
        st.error(f"An error occurred while saving the automated payment: {e}")

def load_automated_payments_from_database():
    try:
        conn = sqlite3.connect('finance_data.db')
        cursor = conn.cursor()
        
        # Create automated_payments table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS automated_payments
        (Name TEXT, Amount REAL, Frequency TEXT, NextPaymentDate TEXT, User TEXT)
        ''')
        
        df = pd.read_sql('SELECT * FROM automated_payments', conn)
        conn.close()
        return df
    except sqlite3.Error as e:
        st.error(f"An error occurred while loading automated payments: {e}")
        return pd.DataFrame()

def save_loan_to_database(df):
    try:
        conn = sqlite3.connect('finance_data.db')
        cursor = conn.cursor()
        
        # Create loans table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS loans
        (Name TEXT, Amount REAL, Type TEXT, DueDate TEXT, User TEXT)
        ''')
        
        df.to_sql('loans', conn, if_exists='append', index=False)
        conn.close()
    except sqlite3.Error as e:
        st.error(f"An error occurred while saving the loan: {e}")

def load_loans_from_database():
    try:
        conn = sqlite3.connect('finance_data.db')
        cursor = conn.cursor()
        
        # Create loans table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS loans
        (Name TEXT, Amount REAL, Type TEXT, DueDate TEXT, User TEXT)
        ''')
        
        df = pd.read_sql('SELECT * FROM loans', conn)
        conn.close()
        return df
    except sqlite3.Error as e:
        st.error(f"An error occurred while loading loans: {e}")
        return pd.DataFrame()

# Initialize the app
if __name__ == "__main__":
    main()