import sqlitecloud as sqlite3
import hashlib
from datetime import datetime, date
import os
from dotenv import load_dotenv
import traceback
from logger import db_logger, LoggingContextManager, log_exception
import streamlit as st

# Load environment variables from .env file
load_dotenv()
# Register adapters and converters for date handling
sqlite3.register_adapter(date, lambda d: d.isoformat())
sqlite3.register_converter("DATE", lambda s: datetime.strptime(s.decode(), "%Y-%m-%d").date())

class DatabaseManager:
    def __init__(self, sql_url=st.secrets.get("SQL_URL")):
        self.sql_url = sql_url
        db_logger.info("DatabaseManager initialized")
        try:
            self.init_database()
        except Exception as e:
            db_logger.error(f"Failed to initialize database: {str(e)}")
            db_logger.debug(f"Traceback: {traceback.format_exc()}")
            raise
    def get_connection(self):
        """Get database connection with error handling"""
        try:
            connection = sqlite3.connect(self.sql_url)
            db_logger.debug("Database connection established")
            return connection
        except Exception as e:
            db_logger.error(f"Error connecting to database: {str(e)}")
            db_logger.debug(f"Traceback: {traceback.format_exc()}")
            raise
    
    def init_database(self):
        """Initialize database with required tables"""
        with LoggingContextManager(db_logger, "init_database"):
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create users table
            db_logger.info("Creating users table if not exists")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create expenses table
            db_logger.info("Creating expenses table if not exists")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL NOT NULL,
                    purpose TEXT NOT NULL,
                    category TEXT NOT NULL,
                    date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            

            
            conn.commit()
            conn.close()
            db_logger.info("Database initialization completed successfully")
    def authenticate_user(self, username, password):
        """Authenticate user login"""
        with LoggingContextManager(db_logger, f"authenticate_user for '{username}'"):
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                cursor.execute('''
                    SELECT id, username, full_name FROM users 
                    WHERE username = ? AND password_hash = ?
                ''', (username, password_hash))
                
                user = cursor.fetchone()
                
                if user:
                    db_logger.info(f"User '{username}' authenticated successfully")
                    return {"id": user[0], "username": user[1], "full_name": user[2]}
                else:
                    db_logger.warning(f"Authentication failed for user '{username}'")
                    return None
            except Exception as e:
                db_logger.error(f"Error during authentication for user '{username}': {str(e)}")
                raise
            finally:
                conn.close()
    def add_expense(self, user_id, amount, purpose, category, date):
        """Add new expense"""
        with LoggingContextManager(db_logger, f"add_expense for user_id={user_id}"):
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO expenses (user_id, amount, purpose, category, date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, amount, purpose, category, date))
                
                expense_id = cursor.lastrowid
                conn.commit()
                db_logger.info(f"Expense added: ID={expense_id}, user_id={user_id}, amount={amount}, category={category}")
                return True
            except Exception as e:
                db_logger.error(f"Failed to add expense for user_id={user_id}: {str(e)}")
                conn.rollback()
                raise
            finally:
                conn.close()
    def get_user_expenses(self, user_id, start_date=None, end_date=None):
        """Get expenses for a specific user"""
        with LoggingContextManager(db_logger, f"get_user_expenses for user_id={user_id}"):
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                query = '''
                    SELECT id, amount, purpose, category, date, created_at
                    FROM expenses 
                    WHERE user_id = ?
                '''
                params = [user_id]
                
                if start_date and end_date:
                    query += ' AND date BETWEEN ? AND ?'
                    params.extend([start_date, end_date])
                    db_logger.debug(f"Date filter applied: {start_date} to {end_date}")
                
                query += ' ORDER BY date DESC'
                
                cursor.execute(query, params)
                expenses = cursor.fetchall()
                db_logger.info(f"Retrieved {len(expenses)} expenses for user_id={user_id}")
                return expenses
            except Exception as e:
                db_logger.error(f"Error fetching expenses for user_id={user_id}: {str(e)}")
                raise
            finally:
                conn.close()
    def get_all_expenses(self, start_date=None, end_date=None):
        """Get all expenses (for partner view)"""
        with LoggingContextManager(db_logger, "get_all_expenses"):
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                query = '''
                    SELECT e.id, e.amount, e.purpose, e.category, e.date, u.full_name
                    FROM expenses e
                    JOIN users u ON e.user_id = u.id
                '''
                params = []
                
                if start_date and end_date:
                    query += ' WHERE e.date BETWEEN ? AND ?'
                    params.extend([start_date, end_date])
                    db_logger.debug(f"Date filter applied: {start_date} to {end_date}")
                
                query += ' ORDER BY e.date DESC'
                
                cursor.execute(query, params)
                expenses = cursor.fetchall()
                db_logger.info(f"Retrieved {len(expenses)} total expenses")
                return expenses
            except Exception as e:
                db_logger.error(f"Error fetching all expenses: {str(e)}")
                raise
            finally:
                conn.close()
    def get_category_summary(self, user_id=None, start_date=None, end_date=None):
        """Get spending summary by category"""
        with LoggingContextManager(db_logger, "get_category_summary"):
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                query = '''
                    SELECT category, SUM(amount) as total_amount, COUNT(*) as count
                    FROM expenses
                '''
                params = []
                
                conditions = []
                if user_id:
                    conditions.append('user_id = ?')
                    params.append(user_id)
                    db_logger.debug(f"User filter applied: user_id={user_id}")
                
                if start_date and end_date:
                    conditions.append('date BETWEEN ? AND ?')
                    params.extend([start_date, end_date])
                    db_logger.debug(f"Date filter applied: {start_date} to {end_date}")
                
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
                
                query += ' GROUP BY category ORDER BY total_amount DESC'
                
                cursor.execute(query, params)
                summary = cursor.fetchall()
                db_logger.info(f"Retrieved category summary with {len(summary)} categories")
                return summary
            except Exception as e:
                db_logger.error(f"Error getting category summary: {str(e)}")
                raise
            finally:
                conn.close()
    def get_monthly_summary(self, user_id=None):
        """Get monthly spending summary"""
        with LoggingContextManager(db_logger, "get_monthly_summary"):
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                query = '''
                    SELECT strftime('%Y-%m', date) as month, SUM(amount) as total_amount
                    FROM expenses
                '''
                params = []
                
                if user_id:
                    query += ' WHERE user_id = ?'
                    params.append(user_id)
                    db_logger.debug(f"User filter applied: user_id={user_id}")
                
                query += ' GROUP BY strftime("%Y-%m", date) ORDER BY month DESC LIMIT 12'
                
                cursor.execute(query, params)
                summary = cursor.fetchall()
                db_logger.info(f"Retrieved monthly summary with {len(summary)} months of data")
                return summary
            except Exception as e:
                db_logger.error(f"Error getting monthly summary: {str(e)}")
                raise
            finally:
                conn.close()
                
    def get_expense_by_id(self, expense_id):
        """Get a specific expense by ID"""
        with LoggingContextManager(db_logger, f"get_expense_by_id for expense_id={expense_id}"):
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    SELECT id, user_id, amount, purpose, category, date, created_at
                    FROM expenses 
                    WHERE id = ?
                ''', (expense_id,))
                
                expense = cursor.fetchone()
                
                if expense:
                    db_logger.info(f"Retrieved expense with ID={expense_id}")
                    # Return as dictionary for easier handling
                    return {
                        "id": expense[0],
                        "user_id": expense[1],
                        "amount": expense[2],
                        "purpose": expense[3],
                        "category": expense[4],
                        "date": expense[5],
                        "created_at": expense[6]
                    }
                else:
                    db_logger.warning(f"No expense found with ID={expense_id}")
                    return None
            except Exception as e:
                db_logger.error(f"Error fetching expense with ID={expense_id}: {str(e)}")
                raise
            finally:
                conn.close()
    
    def update_expense(self, expense_id, amount, purpose, category, date):
        """Update an existing expense"""
        with LoggingContextManager(db_logger, f"update_expense for expense_id={expense_id}"):
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                # First check if the expense exists and get the current values
                existing_expense = self.get_expense_by_id(expense_id)
                if not existing_expense:
                    db_logger.warning(f"Attempted to update non-existent expense with ID={expense_id}")
                    return False
                
                cursor.execute('''
                    UPDATE expenses 
                    SET amount = ?, purpose = ?, category = ?, date = ?
                    WHERE id = ?
                ''', (amount, purpose, category, date, expense_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    db_logger.info(f"Expense updated: ID={expense_id}, amount={amount}, category={category}")
                    return True
                else:
                    db_logger.warning(f"No changes made to expense with ID={expense_id}")
                    return False
            except Exception as e:
                db_logger.error(f"Failed to update expense with ID={expense_id}: {str(e)}")
                conn.rollback()
                raise
            finally:
                conn.close()
    
    def delete_expense(self, expense_id):
        """Delete an expense"""
        with LoggingContextManager(db_logger, f"delete_expense for expense_id={expense_id}"):
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                # First check if the expense exists
                existing_expense = self.get_expense_by_id(expense_id)
                if not existing_expense:
                    db_logger.warning(f"Attempted to delete non-existent expense with ID={expense_id}")
                    return False
                
                cursor.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    db_logger.info(f"Expense deleted: ID={expense_id}")
                    return True
                else:
                    db_logger.warning(f"Failed to delete expense with ID={expense_id}")
                    return False
            except Exception as e:
                db_logger.error(f"Error deleting expense with ID={expense_id}: {str(e)}")
                conn.rollback()
                raise
            finally:
                conn.close()
                
    # User Management Methods
    def get_all_users(self):
        """Get all users in the system"""
        with LoggingContextManager(db_logger, "get_all_users"):
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    SELECT id, username, full_name, created_at
                    FROM users
                    ORDER BY username
                ''')
                
                users = cursor.fetchall()
                db_logger.info(f"Retrieved {len(users)} users")
                
                # Convert to list of dictionaries for easier handling
                result = []
                for user in users:
                    result.append({
                        "id": user[0],
                        "username": user[1],
                        "full_name": user[2],
                        "created_at": user[3]
                    })
                return result
            except Exception as e:
                db_logger.error(f"Error fetching users: {str(e)}")
                raise
            finally:
                conn.close()
    
    def get_user_by_id(self, user_id):
        """Get a specific user by ID"""
        with LoggingContextManager(db_logger, f"get_user_by_id for user_id={user_id}"):
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    SELECT id, username, full_name, created_at
                    FROM users 
                    WHERE id = ?
                ''', (user_id,))
                
                user = cursor.fetchone()
                
                if user:
                    db_logger.info(f"Retrieved user with ID={user_id}")
                    return {
                        "id": user[0],
                        "username": user[1],
                        "full_name": user[2],
                        "created_at": user[3]
                    }
                else:
                    db_logger.warning(f"No user found with ID={user_id}")
                    return None
            except Exception as e:
                db_logger.error(f"Error fetching user with ID={user_id}: {str(e)}")
                raise
            finally:
                conn.close()
    
    def username_exists(self, username, exclude_user_id=None):
        """Check if a username already exists (excluding a specific user)"""
        with LoggingContextManager(db_logger, f"username_exists check for '{username}'"):
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                if exclude_user_id:
                    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ? AND id != ?', 
                                  (username, exclude_user_id))
                else:
                    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', (username,))
                
                count = cursor.fetchone()[0]
                exists = count > 0
                
                db_logger.debug(f"Username '{username}' exists: {exists}")
                return exists
            except Exception as e:
                db_logger.error(f"Error checking if username '{username}' exists: {str(e)}")
                raise
            finally:
                conn.close()
    
    def add_user(self, username, password, full_name):
        """Add a new user"""
        with LoggingContextManager(db_logger, f"add_user '{username}'"):
            # Check if username already exists
            if self.username_exists(username):
                db_logger.warning(f"Cannot add user: Username '{username}' already exists")
                return False, "Username already exists"
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                # Hash the password
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                
                cursor.execute('''
                    INSERT INTO users (username, password_hash, full_name)
                    VALUES (?, ?, ?)
                ''', (username, password_hash, full_name))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                db_logger.info(f"New user added: ID={user_id}, username='{username}', full_name='{full_name}'")
                return True, user_id
            except Exception as e:
                db_logger.error(f"Error adding user '{username}': {str(e)}")
                conn.rollback()
                raise
            finally:
                conn.close()
    
    def update_username(self, user_id, new_username):
        """Update a user's username"""
        with LoggingContextManager(db_logger, f"update_username for user_id={user_id}"):
            # Check if user exists
            user = self.get_user_by_id(user_id)
            if not user:
                db_logger.warning(f"Cannot update username: User with ID={user_id} does not exist")
                return False, "User not found"
            
            # Check if new username already exists for another user
            if self.username_exists(new_username, exclude_user_id=user_id):
                db_logger.warning(f"Cannot update username: Username '{new_username}' already exists")
                return False, "Username already exists"
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    UPDATE users
                    SET username = ?
                    WHERE id = ?
                ''', (new_username, user_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    db_logger.info(f"Username updated for user ID={user_id}: '{user['username']}' -> '{new_username}'")
                    return True, "Username updated successfully"
                else:
                    db_logger.warning(f"No changes made to username for user ID={user_id}")
                    return False, "No changes made"
            except Exception as e:
                db_logger.error(f"Error updating username for user ID={user_id}: {str(e)}")
                conn.rollback()
                raise
            finally:
                conn.close()
    
    def update_password(self, user_id, current_password, new_password):
        """Update a user's password"""
        with LoggingContextManager(db_logger, f"update_password for user_id={user_id}"):
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                # Verify current password
                current_hash = hashlib.sha256(current_password.encode()).hexdigest()
                cursor.execute('''
                    SELECT COUNT(*)
                    FROM users
                    WHERE id = ? AND password_hash = ?
                ''', (user_id, current_hash))
                
                if cursor.fetchone()[0] == 0:
                    db_logger.warning(f"Password update failed for user ID={user_id}: Current password is incorrect")
                    return False, "Current password is incorrect"
                
                # Hash the new password
                new_hash = hashlib.sha256(new_password.encode()).hexdigest()
                
                # Update the password
                cursor.execute('''
                    UPDATE users
                    SET password_hash = ?
                    WHERE id = ?
                ''', (new_hash, user_id))
                
                conn.commit()
                
                db_logger.info(f"Password updated for user ID={user_id}")
                return True, "Password updated successfully"
            except Exception as e:
                db_logger.error(f"Error updating password for user ID={user_id}: {str(e)}")
                conn.rollback()
                raise
            finally:
                conn.close()
    
    def update_full_name(self, user_id, new_full_name):
        """Update a user's full name"""
        with LoggingContextManager(db_logger, f"update_full_name for user_id={user_id}"):
            # Check if user exists
            user = self.get_user_by_id(user_id)
            if not user:
                db_logger.warning(f"Cannot update full name: User with ID={user_id} does not exist")
                return False, "User not found"
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    UPDATE users
                    SET full_name = ?
                    WHERE id = ?
                ''', (new_full_name, user_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    db_logger.info(f"Full name updated for user ID={user_id}: '{user['full_name']}' -> '{new_full_name}'")
                    return True, "Full name updated successfully"
                else:
                    db_logger.warning(f"No changes made to full name for user ID={user_id}")
                    return False, "No changes made"
            except Exception as e:
                db_logger.error(f"Error updating full name for user ID={user_id}: {str(e)}")
                conn.rollback()
                raise
            finally:
                conn.close()
    
    def delete_user(self, user_id):
        """Delete a user but keep their expenses"""
        with LoggingContextManager(db_logger, f"delete_user for user_id={user_id}"):
            # Check if user exists
            user = self.get_user_by_id(user_id)
            if not user:
                db_logger.warning(f"Cannot delete user: User with ID={user_id} does not exist")
                return False, "User not found"
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                # Get expense count for this user
                cursor.execute('SELECT COUNT(*) FROM expenses WHERE user_id = ?', (user_id,))
                expense_count = cursor.fetchone()[0]
                
                # Delete the user
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    db_logger.info(f"User deleted: ID={user_id}, username='{user['username']}' (keeping {expense_count} expenses)")
                    return True, f"User deleted (kept {expense_count} expenses in the system)"
                else:
                    db_logger.warning(f"Failed to delete user with ID={user_id}")
                    return False, "Failed to delete user"
            except Exception as e:
                db_logger.error(f"Error deleting user with ID={user_id}: {str(e)}")
                conn.rollback()
                raise
            finally:
                conn.close()