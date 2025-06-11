import sqlitecloud as sqlite3
import hashlib
from datetime import datetime, date
import os
from dotenv import load_dotenv
import traceback
from logger import db_logger, LoggingContextManager, log_exception

# Load environment variables from .env file
load_dotenv()

# Register adapters and converters for date handling
sqlite3.register_adapter(date, lambda d: d.isoformat())
sqlite3.register_converter("DATE", lambda s: datetime.strptime(s.decode(), "%Y-%m-%d").date())

class DatabaseManager:
    def __init__(self, sql_url=os.getenv("SQL_URL")):
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
            
            # Insert predefined users if they don't exist
            self.create_default_users(cursor)
            
            conn.commit()
            conn.close()
            db_logger.info("Database initialization completed successfully")
    def create_default_users(self, cursor):
        """Create three predefined users"""
        with LoggingContextManager(db_logger, "create_default_users"):
            default_users = [
                ("sana", "Sudhakar", "admin@123$"),
                ("harsi", "Harshitha", "admin@123$"),
                ("pandu", "swetha", "admin@123$")
            ]
            
            db_logger.info(f"Creating {len(default_users)} default users if they don't exist")
            for username, full_name, password in default_users:
                try:
                    password_hash = hashlib.sha256(password.encode()).hexdigest()
                    cursor.execute('''
                        INSERT OR IGNORE INTO users (username, password_hash, full_name)
                        VALUES (?, ?, ?)
                    ''', (username, password_hash, full_name))
                    db_logger.debug(f"Default user '{username}' processed")
                except Exception as e:
                    db_logger.error(f"Failed to create default user '{username}': {str(e)}")
                    # Continue with other users despite errors
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