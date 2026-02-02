# KWASNY LOG MANAGER - Quick Start Guide

## 🚀 Quick Start (5 minutes)

### Step 1: Clone and Setup
```bash
# Clone repository
git clone https://github.com/malykatamaranek-eng/KwasnySzpontMenager.git
cd KwasnySzpontMenager

# Run setup script
# Linux/Mac:
./setup.sh

# Windows:
setup.bat
```

### Step 2: Configure
```bash
# Copy example configs
cp config/proxies.txt.example config/proxies.txt
cp config/accounts.txt.example config/accounts.txt

# Edit with your data
nano config/proxies.txt    # Add your proxies
nano config/accounts.txt   # Add your accounts
```

### Step 3: Run
```bash
# Option A: GUI (recommended for first time)
python -m src.gui.admin_panel

# Option B: CLI
python cli.py init          # Initialize system
python cli.py list          # List accounts
python cli.py process       # Process all accounts
python cli.py stats         # Show statistics

# Option C: Direct Python
python -m src.main
```

## 📝 Configuration Files Explained

### config/proxies.txt
One proxy per line:
```
socks5://user:pass@192.168.1.1:1080
socks5://192.168.1.2:1080
http://user:pass@192.168.1.3:8080
```

### config/accounts.txt
Format: `email:password` or `email:password:facebook_password`
```
user1@wp.pl:emailpass123
user2@onet.pl:emailpass456:fbpass456
```

### config/financial_config.ini
Adjust costs and revenues:
```ini
[Financial]
proxy_cost_daily = 0.15        # Cost of proxy per day
account_cost_total = 3.00      # One-time account purchase cost
daily_revenue = 1.50           # Expected daily revenue
default_activity_percentage = 85.0
```

### config/system_settings.ini
System behavior:
```ini
[System]
max_parallel_accounts = 5      # How many accounts to process at once
headless_browser = true        # Run browser in background
default_facebook_password = NewSecurePass123!
```

## 🎮 Using the GUI

1. **Launch GUI**: `python -m src.gui.admin_panel`

2. **Initialize System**: Click "🔄 Inicjalizuj System"
   - Loads proxies from config/proxies.txt
   - Loads accounts from config/accounts.txt
   - Assigns unique proxy to each account

3. **Select Account**: Click on any account in the left panel

4. **Process Account**: Click "▶️ Przetwórz"
   - Logs into email
   - Logs into Facebook (auto-reset password if needed)
   - Performs security scan
   - Updates financial data

5. **View Details**: See logs, financial stats, and account info in right panel

## 🖥️ Using the CLI

### Initialize system
```bash
python cli.py init
```

### List all accounts
```bash
python cli.py list
```

### Process specific account
```bash
python cli.py process -a 1
```

### Process all accounts
```bash
python cli.py process
```

### Process in parallel (faster)
```bash
python cli.py process -p
```

### View statistics
```bash
# Global stats
python cli.py stats

# Specific account
python cli.py stats -a 1
```

### View logs
```bash
# Recent logs
python cli.py logs

# Logs for specific account
python cli.py logs -a 1

# More logs
python cli.py logs -l 50
```

## 🔍 Troubleshooting

### "No module named 'playwright'"
```bash
pip install -r requirements.txt
playwright install chromium
```

### "No proxies available"
1. Check `config/proxies.txt` exists and has proxies
2. Run `python cli.py init`
3. Verify proxies are working

### "Account not found"
1. Check `config/accounts.txt` exists and has accounts
2. Run `python cli.py init`
3. Check database: `python cli.py list`

### Timeout errors
1. Increase timeout in `config/system_settings.ini`:
   ```ini
   operation_timeout = 60
   ```
2. Check internet connection
3. Verify proxy works

### Browser won't start
1. Reinstall Playwright:
   ```bash
   playwright install chromium
   ```
2. Run in visible mode (for debugging):
   Edit `config/system_settings.ini`:
   ```ini
   headless_browser = false
   ```

## 📊 Understanding the Output

### Email Statuses
- ✅ **POCZTA_DZIAŁA** - Email login successful
- ❌ **BŁĘDNE_HASŁO** - Wrong password
- ❌ **KONTO_NIEISTNIEJE** - Account doesn't exist
- ⚠️ **WYMAGANA_2FA** - 2FA required
- 🔒 **KONTO_ZABLOKOWANE** - Account blocked

### Facebook Statuses
- ✅ **LOGIN_SUKCES** - Login successful
- ❌ **WRONG_PASSWORD** - Wrong password (will auto-reset)
- 🔄 **CHECKPOINT_REQUIRED** - Verification required
- 🔐 **TWO_FACTOR_ENABLED** - 2FA is active
- 🚫 **ACCOUNT_DISABLED** - Account disabled

### Financial Display
```
┌───────────────────────────────────────┐
│ KONTO: user@wp.pl                     │
│ Status: ✅ AKTYWNE                    │
│ Dni aktywności: 15                    │
│                                        │
│ KOSZTY:                               │
│  • Proxy: $0.15/dzień                 │
│  • Konto: $0.03/dzień (amortyzacja)   │
│  • Email: $0.01/dzień                 │
│  • Operacyjny: $0.05/dzień            │
│  → DZIENNY KOSZT: $0.24               │
│                                        │
│ PRZYCHODY:                            │
│  • Dzienny przychód: $1.50            │
│  • Aktywność: 85%                     │
│  → DZIENNY PRZYCHÓD: $1.27            │
│                                        │
│ ZYSK:                                 │
│  • Dzienny: $1.03                     │
│  • Łączny: $15.45                     │
└───────────────────────────────────────┘
```

## 🎯 Best Practices

1. **Start Small**: Test with 1-2 accounts first
2. **Monitor Logs**: Check logs regularly for issues
3. **Backup Database**: Copy `data/kwasny.db` regularly
4. **Test Proxies**: Ensure proxies work before use
5. **Secure Configs**: Never commit `config/accounts.txt` or `config/proxies.txt`
6. **Schedule**: Run daily security scans
7. **Financial Tracking**: Review statistics weekly

## 📈 Daily Workflow

1. **Morning**: Run `python cli.py process` to process all accounts
2. **Check**: Run `python cli.py stats` to see financial summary
3. **Review**: Check `python cli.py logs` for any issues
4. **Evening**: Run security scans if needed

## 🔒 Security Notes

- Each account uses a unique proxy (IP isolation)
- No data sharing between accounts
- Randomized user agents and timings
- Anti-detection measures built-in
- Sensitive configs in .gitignore

## 📚 More Information

- Full documentation: See README.md
- Module details: Check docstrings in source files
- Database schema: See src/database.py
- Configuration: All files in config/

## 🆘 Getting Help

1. Check logs: `python cli.py logs`
2. Test system: `python test_system.py`
3. Review README.md for detailed documentation
4. Check source code comments for technical details

---

**Ready to start?**
```bash
python -m src.gui.admin_panel
```
