#!/usr/bin/env python3
"""
KWASNY LOG MANAGER - CLI Interface
Quick command-line interface for common operations
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.main import KwasnyLogManager
from src.database import Database


def cmd_init(args):
    """Initialize system with config files"""
    manager = KwasnyLogManager()
    print("🔄 Initializing system...")
    manager.initialize_system()
    print("✅ System initialized!")


def cmd_list(args):
    """List all accounts"""
    manager = KwasnyLogManager()
    manager.list_all_accounts()


def cmd_process(args):
    """Process accounts"""
    manager = KwasnyLogManager()
    
    if args.account_id:
        print(f"🔄 Processing account ID {args.account_id}...")
        result = asyncio.run(manager.process_single_account(args.account_id))
        
        if result.get('success'):
            print(f"✅ Account processed successfully!")
        else:
            print(f"❌ Processing failed!")
            for error in result.get('errors', []):
                print(f"   • {error}")
    else:
        print("🔄 Processing all accounts...")
        asyncio.run(manager.process_all_accounts(parallel=args.parallel))


def cmd_stats(args):
    """Show statistics"""
    manager = KwasnyLogManager()
    
    if args.account_id:
        # Show account details
        manager.display_account_details(args.account_id)
    else:
        # Show global statistics
        global_stats = manager.financial_calculator.get_global_statistics()
        
        print("\n" + "="*60)
        print("📊 GLOBAL STATISTICS")
        print("="*60)
        print(f"Total accounts: {global_stats['total_accounts']}")
        print(f"Total profit: ${global_stats['total_profit']:.2f}")
        print(f"Daily revenue: ${global_stats['total_daily_revenue']:.2f}")
        print(f"Daily cost: ${global_stats['total_daily_cost']:.2f}")
        print(f"Avg profit/account: ${global_stats['avg_profit_per_account']:.2f}")
        print(f"ROI: {global_stats['roi_percentage']:.1f}%")
        print(f"Losing accounts: {global_stats['losing_accounts_count']}")
        
        if global_stats['most_profitable']:
            mp = global_stats['most_profitable']
            print(f"\nMost profitable: {mp['email']}")
            print(f"  Profit: ${mp['summary']['total_profit']:.2f}")


def cmd_logs(args):
    """Show logs"""
    db = Database()
    
    if args.account_id:
        logs = db.get_account_logs(args.account_id, limit=args.limit)
        account = db.get_account(args.account_id)
        
        if account:
            print(f"\n📋 Logs for {account['email']} (last {len(logs)} entries)")
            print("="*80)
            
            for log in logs:
                print(f"[{log['timestamp']}] {log['action']}: {log['status']}")
                if log['details']:
                    print(f"  ↳ {log['details']}")
                if log['duration']:
                    print(f"  ⏱ {log['duration']:.2f}s")
                print()
    else:
        # Show all recent logs
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT l.*, a.email 
            FROM logs l
            JOIN accounts a ON l.account_id = a.id
            ORDER BY l.timestamp DESC
            LIMIT ?
        """, (args.limit,))
        
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        print(f"\n📋 Recent logs (last {len(logs)} entries)")
        print("="*80)
        
        for log in logs:
            print(f"[{log['timestamp']}] {log['email']}")
            print(f"  {log['action']}: {log['status']}")
            if log['details']:
                print(f"  ↳ {log['details']}")
            print()


def cmd_gui(args):
    """Launch GUI"""
    print("🚀 Launching GUI...")
    from src.gui.admin_panel import main
    main()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='KWASNY LOG MANAGER - Command Line Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s init                    # Initialize system with config files
  %(prog)s list                    # List all accounts
  %(prog)s process                 # Process all accounts
  %(prog)s process -a 1            # Process account ID 1
  %(prog)s process -p              # Process all accounts in parallel
  %(prog)s stats                   # Show global statistics
  %(prog)s stats -a 1              # Show statistics for account ID 1
  %(prog)s logs                    # Show recent logs
  %(prog)s logs -a 1               # Show logs for account ID 1
  %(prog)s gui                     # Launch GUI
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    parser_init = subparsers.add_parser('init', help='Initialize system')
    parser_init.set_defaults(func=cmd_init)
    
    # List command
    parser_list = subparsers.add_parser('list', help='List all accounts')
    parser_list.set_defaults(func=cmd_list)
    
    # Process command
    parser_process = subparsers.add_parser('process', help='Process accounts')
    parser_process.add_argument('-a', '--account-id', type=int, help='Process specific account ID')
    parser_process.add_argument('-p', '--parallel', action='store_true', help='Process accounts in parallel')
    parser_process.set_defaults(func=cmd_process)
    
    # Stats command
    parser_stats = subparsers.add_parser('stats', help='Show statistics')
    parser_stats.add_argument('-a', '--account-id', type=int, help='Show stats for specific account')
    parser_stats.set_defaults(func=cmd_stats)
    
    # Logs command
    parser_logs = subparsers.add_parser('logs', help='Show logs')
    parser_logs.add_argument('-a', '--account-id', type=int, help='Show logs for specific account')
    parser_logs.add_argument('-l', '--limit', type=int, default=20, help='Number of log entries to show')
    parser_logs.set_defaults(func=cmd_logs)
    
    # GUI command
    parser_gui = subparsers.add_parser('gui', help='Launch GUI')
    parser_gui.set_defaults(func=cmd_gui)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    try:
        args.func(args)
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
