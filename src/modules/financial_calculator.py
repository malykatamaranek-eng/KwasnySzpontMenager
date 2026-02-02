"""
MODUŁ 5: STATYSTYKI FINANSOWE
Kalkulacja kosztów, przychodów i zysków per konto
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class FinancialConfig:
    """Financial configuration for calculations"""
    proxy_cost_daily: float = 0.15
    account_cost_total: float = 3.00  # Total cost of account
    account_amortization_days: int = 30  # Amortize over 30 days
    email_cost_total: float = 0.30
    email_amortization_days: int = 30
    operational_cost_daily: float = 0.05
    daily_revenue: float = 1.50
    default_activity_percentage: float = 85.0
    
    @property
    def account_cost_daily(self) -> float:
        return self.account_cost_total / self.account_amortization_days
    
    @property
    def email_cost_daily(self) -> float:
        return self.email_cost_total / self.email_amortization_days


class FinancialCalculator:
    """
    Calculate financial statistics for accounts
    """
    
    def __init__(self, database, config: Optional[FinancialConfig] = None):
        self.database = database
        self.config = config or FinancialConfig()
    
    def calculate_daily_profit(self, account_id: int, date: str = None) -> float:
        """
        Calculate daily profit for an account
        Formula: DAILY_PROFIT = (DAILY_REVENUE * ACTIVITY) - DAILY_COST
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Get or create financial data for this date
        conn = self.database.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM financial_data
            WHERE account_id = ? AND date = ?
        """, (account_id, date))
        
        data = cursor.fetchone()
        
        if data:
            conn.close()
            return data['calculated_profit']
        
        # Create new entry with default values
        total_cost = (
            self.config.proxy_cost_daily +
            self.config.account_cost_daily +
            self.config.email_cost_daily +
            self.config.operational_cost_daily
        )
        
        actual_revenue = self.config.daily_revenue * (self.config.default_activity_percentage / 100.0)
        calculated_profit = actual_revenue - total_cost
        
        cursor.execute("""
            INSERT INTO financial_data 
            (account_id, date, proxy_cost, account_cost_daily, email_cost_daily,
             operational_cost, daily_revenue, activity_percentage, calculated_profit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            account_id, date,
            self.config.proxy_cost_daily,
            self.config.account_cost_daily,
            self.config.email_cost_daily,
            self.config.operational_cost_daily,
            self.config.daily_revenue,
            self.config.default_activity_percentage,
            calculated_profit
        ))
        
        conn.commit()
        conn.close()
        
        return calculated_profit
    
    def get_account_summary(self, account_id: int) -> Dict:
        """
        Get comprehensive financial summary for an account
        """
        summary = self.database.get_account_financial_summary(account_id)
        
        if not summary or summary['days_active'] == 0:
            return {
                'days_active': 0,
                'total_profit': 0.0,
                'avg_daily_profit': 0.0,
                'avg_daily_cost': 0.0,
                'avg_daily_revenue': 0.0,
                'current_daily_cost': self.config.proxy_cost_daily + 
                                     self.config.account_cost_daily + 
                                     self.config.email_cost_daily + 
                                     self.config.operational_cost_daily,
                'current_daily_revenue': self.config.daily_revenue * (self.config.default_activity_percentage / 100.0),
                'current_daily_profit': 0.0
            }
        
        # Calculate current day profit
        current_profit = self.calculate_daily_profit(account_id)
        
        return {
            'days_active': summary['days_active'],
            'total_profit': summary['total_profit'] or 0.0,
            'avg_daily_profit': summary['avg_daily_profit'] or 0.0,
            'avg_daily_cost': summary['avg_daily_cost'] or 0.0,
            'avg_daily_revenue': summary['avg_daily_revenue'] or 0.0,
            'current_daily_cost': self.config.proxy_cost_daily + 
                                 self.config.account_cost_daily + 
                                 self.config.email_cost_daily + 
                                 self.config.operational_cost_daily,
            'current_daily_revenue': self.config.daily_revenue * (self.config.default_activity_percentage / 100.0),
            'current_daily_profit': current_profit
        }
    
    def format_account_summary(self, account_id: int) -> str:
        """
        Format account summary as text box (for display)
        """
        account = self.database.get_account(account_id)
        if not account:
            return "Account not found"
        
        summary = self.get_account_summary(account_id)
        
        status_emoji = "✅" if account['active'] else "❌"
        
        text = f"""
┌───────────────────────────────────────┐
│ KONTO: {account['email']:<28} │
│ Status: {status_emoji} {'AKTYWNE' if account['active'] else 'NIEAKTYWNE':<26} │
│ Dni aktywności: {summary['days_active']:<22} │
│                                        │
│ KOSZTY:                               │
│  • Proxy: ${self.config.proxy_cost_daily:.2f}/dzień{' ' * 18} │
│  • Konto: ${self.config.account_cost_daily:.2f}/dzień (amortyzacja){' ' * 3} │
│  • Email: ${self.config.email_cost_daily:.2f}/dzień{' ' * 18} │
│  • Operacyjny: ${self.config.operational_cost_daily:.2f}/dzień{' ' * 13} │
│  → DZIENNY KOSZT: ${summary['current_daily_cost']:.2f}{' ' * 13} │
│                                        │
│ PRZYCHODY:                            │
│  • Dzienny przychód: ${self.config.daily_revenue:.2f}{' ' * 12} │
│  • Aktywność: {self.config.default_activity_percentage:.0f}%{' ' * 21} │
│  → DZIENNY PRZYCHÓD: ${summary['current_daily_revenue']:.2f}{' ' * 10} │
│                                        │
│ ZYSK:                                 │
│  • Dzienny: ${summary['current_daily_profit']:.2f}{' ' * 20} │
│  • Łączny: ${summary['total_profit']:.2f}{' ' * 21} │
└───────────────────────────────────────┘
        """
        
        return text.strip()
    
    def get_global_statistics(self) -> Dict:
        """
        Get global statistics for all accounts
        """
        accounts = self.database.get_all_accounts(active_only=True)
        
        total_profit = 0.0
        total_revenue = 0.0
        total_cost = 0.0
        account_summaries = []
        
        for account in accounts:
            summary = self.get_account_summary(account['id'])
            account_summaries.append({
                'account_id': account['id'],
                'email': account['email'],
                'summary': summary
            })
            
            total_profit += summary['total_profit']
            total_revenue += summary['current_daily_revenue']
            total_cost += summary['current_daily_cost']
        
        # Sort by profit (most profitable first)
        account_summaries.sort(key=lambda x: x['summary']['total_profit'], reverse=True)
        
        # Find losing accounts (negative profit)
        losing_accounts = [acc for acc in account_summaries if acc['summary']['total_profit'] < 0]
        
        # Calculate ROI
        total_investment = len(accounts) * (self.config.account_cost_total + self.config.email_cost_total)
        roi = (total_profit / total_investment * 100) if total_investment > 0 else 0
        
        return {
            'total_accounts': len(accounts),
            'total_profit': total_profit,
            'total_daily_revenue': total_revenue,
            'total_daily_cost': total_cost,
            'avg_profit_per_account': total_profit / len(accounts) if accounts else 0,
            'most_profitable': account_summaries[0] if account_summaries else None,
            'losing_accounts_count': len(losing_accounts),
            'losing_accounts': losing_accounts,
            'roi_percentage': roi
        }
    
    def update_account_financial_data(self, account_id: int, **kwargs):
        """
        Update financial data for an account
        Accepts: proxy_cost, daily_revenue, activity_percentage, etc.
        """
        date = kwargs.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # Get current config values or use provided
        proxy_cost = kwargs.get('proxy_cost', self.config.proxy_cost_daily)
        account_cost = kwargs.get('account_cost_daily', self.config.account_cost_daily)
        email_cost = kwargs.get('email_cost_daily', self.config.email_cost_daily)
        operational_cost = kwargs.get('operational_cost', self.config.operational_cost_daily)
        daily_revenue = kwargs.get('daily_revenue', self.config.daily_revenue)
        activity = kwargs.get('activity_percentage', self.config.default_activity_percentage)
        
        return self.database.update_financial_data(
            account_id,
            date=date,
            proxy_cost=proxy_cost,
            account_cost_daily=account_cost,
            email_cost_daily=email_cost,
            operational_cost=operational_cost,
            daily_revenue=daily_revenue,
            activity_percentage=activity
        )


if __name__ == "__main__":
    # Test financial calculations
    config = FinancialConfig()
    print("Financial Configuration:")
    print(f"  Proxy cost daily: ${config.proxy_cost_daily:.2f}")
    print(f"  Account cost daily: ${config.account_cost_daily:.2f}")
    print(f"  Email cost daily: ${config.email_cost_daily:.2f}")
    print(f"  Operational cost: ${config.operational_cost_daily:.2f}")
    print(f"  Daily revenue: ${config.daily_revenue:.2f}")
    print(f"  Activity: {config.default_activity_percentage:.0f}%")
    
    total_cost = (config.proxy_cost_daily + config.account_cost_daily + 
                  config.email_cost_daily + config.operational_cost_daily)
    actual_revenue = config.daily_revenue * (config.default_activity_percentage / 100.0)
    profit = actual_revenue - total_cost
    
    print(f"\nCalculated:")
    print(f"  Total daily cost: ${total_cost:.2f}")
    print(f"  Actual daily revenue: ${actual_revenue:.2f}")
    print(f"  Daily profit: ${profit:.2f}")
