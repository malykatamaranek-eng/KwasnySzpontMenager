"""
KWASNY LOG MANAGER - Database Schema
SQLite database for managing accounts, proxies, logs, and statistics
"""

import sqlite3
from pathlib import Path
from datetime import datetime
import json


class Database:
    """Database manager for the KWASNY LOG MANAGER system"""
    
    def __init__(self, db_path: str = "data/kwasny.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self.init_database()
    
    def connect(self):
        """Establish database connection"""
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        return self.connection
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                email_password TEXT NOT NULL,
                facebook_email TEXT,
                facebook_password TEXT,
                proxy_id INTEGER,
                email_status TEXT DEFAULT 'NIEZNANY',
                facebook_status TEXT DEFAULT 'NIEZNANY',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_check TIMESTAMP,
                active BOOLEAN DEFAULT 1,
                FOREIGN KEY (proxy_id) REFERENCES proxies(id)
            )
        """)
        
        # Proxies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proxies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proxy_url TEXT UNIQUE NOT NULL,
                proxy_type TEXT NOT NULL,
                last_test TIMESTAMP,
                is_working BOOLEAN DEFAULT 1,
                blacklisted BOOLEAN DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Financial data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                date DATE NOT NULL,
                proxy_cost REAL DEFAULT 0.15,
                account_cost_daily REAL DEFAULT 0.03,
                email_cost_daily REAL DEFAULT 0.01,
                operational_cost REAL DEFAULT 0.05,
                daily_revenue REAL DEFAULT 1.50,
                activity_percentage REAL DEFAULT 85.0,
                calculated_profit REAL,
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                UNIQUE(account_id, date)
            )
        """)
        
        # Logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                proxy_used TEXT,
                duration REAL,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        """)
        
        # Security events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                description TEXT,
                sessions_logged_out INTEGER DEFAULT 0,
                calls_rejected INTEGER DEFAULT 0,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        """)
        
        # Password reset codes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reset_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used BOOLEAN DEFAULT 0,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_account(self, email: str, email_password: str, facebook_email: str = None, 
                    facebook_password: str = None, proxy_id: int = None):
        """Add a new account to the database"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO accounts (email, email_password, facebook_email, facebook_password, proxy_id)
                VALUES (?, ?, ?, ?, ?)
            """, (email, email_password, facebook_email or email, facebook_password, proxy_id))
            
            account_id = cursor.lastrowid
            conn.commit()
            return account_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def add_proxy(self, proxy_url: str, proxy_type: str):
        """Add a new proxy to the database"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO proxies (proxy_url, proxy_type)
                VALUES (?, ?)
            """, (proxy_url, proxy_type))
            
            proxy_id = cursor.lastrowid
            conn.commit()
            return proxy_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def get_account(self, account_id: int):
        """Get account details by ID"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
        account = cursor.fetchone()
        conn.close()
        
        return dict(account) if account else None
    
    def get_all_accounts(self, active_only: bool = True):
        """Get all accounts from the database"""
        conn = self.connect()
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute("SELECT * FROM accounts WHERE active = 1")
        else:
            cursor.execute("SELECT * FROM accounts")
        
        accounts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return accounts
    
    def update_account_status(self, account_id: int, email_status: str = None, 
                            facebook_status: str = None):
        """Update account status"""
        conn = self.connect()
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if email_status:
            updates.append("email_status = ?")
            values.append(email_status)
        
        if facebook_status:
            updates.append("facebook_status = ?")
            values.append(facebook_status)
        
        if updates:
            updates.append("last_check = ?")
            values.append(datetime.now())
            values.append(account_id)
            
            query = f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
        
        conn.close()
    
    def add_log(self, account_id: int, action: str, status: str, 
                details: str = None, proxy_used: str = None, duration: float = None):
        """Add a log entry"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO logs (account_id, action, status, details, proxy_used, duration)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (account_id, action, status, details, proxy_used, duration))
        
        conn.commit()
        conn.close()
    
    def get_account_logs(self, account_id: int, limit: int = 100):
        """Get logs for a specific account"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM logs 
            WHERE account_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (account_id, limit))
        
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return logs
    
    def get_proxy_for_account(self, account_id: int):
        """Get proxy assigned to an account"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.* FROM proxies p
            JOIN accounts a ON a.proxy_id = p.id
            WHERE a.id = ?
        """, (account_id,))
        
        proxy = cursor.fetchone()
        conn.close()
        
        return dict(proxy) if proxy else None
    
    def get_available_proxy(self):
        """Get an available proxy that's not blacklisted"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM proxies 
            WHERE is_working = 1 AND blacklisted = 0
            ORDER BY RANDOM()
            LIMIT 1
        """)
        
        proxy = cursor.fetchone()
        conn.close()
        
        return dict(proxy) if proxy else None
    
    def blacklist_proxy(self, proxy_id: int):
        """Blacklist a proxy"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE proxies 
            SET blacklisted = 1, is_working = 0
            WHERE id = ?
        """, (proxy_id,))
        
        conn.commit()
        conn.close()
    
    def update_financial_data(self, account_id: int, date: str = None, **kwargs):
        """Update or insert financial data for an account"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        conn = self.connect()
        cursor = conn.cursor()
        
        # Calculate profit
        proxy_cost = kwargs.get('proxy_cost', 0.15)
        account_cost = kwargs.get('account_cost_daily', 0.03)
        email_cost = kwargs.get('email_cost_daily', 0.01)
        operational_cost = kwargs.get('operational_cost', 0.05)
        daily_revenue = kwargs.get('daily_revenue', 1.50)
        activity = kwargs.get('activity_percentage', 85.0)
        
        total_cost = proxy_cost + account_cost + email_cost + operational_cost
        actual_revenue = daily_revenue * (activity / 100.0)
        calculated_profit = actual_revenue - total_cost
        
        cursor.execute("""
            INSERT INTO financial_data 
            (account_id, date, proxy_cost, account_cost_daily, email_cost_daily, 
             operational_cost, daily_revenue, activity_percentage, calculated_profit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id, date) DO UPDATE SET
                proxy_cost = excluded.proxy_cost,
                account_cost_daily = excluded.account_cost_daily,
                email_cost_daily = excluded.email_cost_daily,
                operational_cost = excluded.operational_cost,
                daily_revenue = excluded.daily_revenue,
                activity_percentage = excluded.activity_percentage,
                calculated_profit = excluded.calculated_profit
        """, (account_id, date, proxy_cost, account_cost, email_cost, 
              operational_cost, daily_revenue, activity, calculated_profit))
        
        conn.commit()
        conn.close()
        
        return calculated_profit
    
    def get_account_financial_summary(self, account_id: int):
        """Get financial summary for an account"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as days_active,
                SUM(calculated_profit) as total_profit,
                AVG(calculated_profit) as avg_daily_profit,
                AVG(proxy_cost + account_cost_daily + email_cost_daily + operational_cost) as avg_daily_cost,
                AVG(daily_revenue * activity_percentage / 100.0) as avg_daily_revenue
            FROM financial_data
            WHERE account_id = ?
        """, (account_id,))
        
        summary = cursor.fetchone()
        conn.close()
        
        return dict(summary) if summary else None


if __name__ == "__main__":
    # Test database creation
    db = Database()
    print("Database initialized successfully!")
