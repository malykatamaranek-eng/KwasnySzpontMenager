# KWASNY LOG MANAGER - Troubleshooting & FAQ

## 🔧 Common Issues and Solutions

### Installation Issues

#### Issue: "pip install fails"
**Symptom**: Error during `pip install -r requirements.txt`

**Solutions**:
```bash
# Update pip first
python -m pip install --upgrade pip

# Install with verbose output
pip install -r requirements.txt -v

# Install individually if batch fails
pip install playwright
pip install PyQt6
pip install aiohttp
# ... etc
```

#### Issue: "Playwright install fails"
**Symptom**: `playwright install chromium` fails

**Solutions**:
```bash
# Uninstall and reinstall playwright
pip uninstall playwright
pip install playwright==1.40.0
playwright install chromium

# If still fails, try with system dependencies
playwright install --with-deps chromium

# On Linux, you may need:
sudo apt-get update
sudo apt-get install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0
```

#### Issue: "Module not found"
**Symptom**: `ModuleNotFoundError: No module named 'X'`

**Solutions**:
```bash
# Ensure you're in the right directory
cd KwasnySzpontMenager

# Install missing module
pip install <module-name>

# Verify installation
python -c "import <module-name>; print('OK')"
```

---

### Configuration Issues

#### Issue: "No proxies available"
**Symptom**: System says "No proxy available" when processing accounts

**Solutions**:
1. Check if `config/proxies.txt` exists:
   ```bash
   ls -la config/proxies.txt
   ```

2. Verify file format (one proxy per line):
   ```
   socks5://user:pass@192.168.1.1:1080
   socks5://192.168.1.2:1080
   ```

3. Re-initialize system:
   ```bash
   python cli.py init
   ```

4. Check database:
   ```bash
   python cli.py list
   sqlite3 data/kwasny.db "SELECT * FROM proxies"
   ```

#### Issue: "Account not found"
**Symptom**: Selected account doesn't exist in database

**Solutions**:
1. Check if `config/accounts.txt` exists
2. Verify format: `email:password` or `email:password:facebook_password`
3. Run initialization:
   ```bash
   python cli.py init
   ```

#### Issue: "Config file not found"
**Symptom**: System can't find configuration files

**Solutions**:
```bash
# Create from examples
cp config/proxies.txt.example config/proxies.txt
cp config/accounts.txt.example config/accounts.txt

# Verify files exist
ls -la config/
```

---

### Runtime Issues

#### Issue: "Timeout during login"
**Symptom**: Operations timeout after 30 seconds

**Solutions**:
1. Increase timeout in `config/system_settings.ini`:
   ```ini
   operation_timeout = 60
   ```

2. Check internet connection:
   ```bash
   ping google.com
   ```

3. Test proxy manually:
   ```bash
   curl --proxy socks5://user:pass@ip:port https://google.com
   ```

4. Try with visible browser for debugging:
   ```ini
   headless_browser = false
   ```

#### Issue: "Browser won't start"
**Symptom**: Playwright browser fails to launch

**Solutions**:
```bash
# Reinstall chromium
playwright install chromium --force

# Check browser path
playwright show-browsers

# Try different browser (in code, modify to use firefox)
# browser = await p.firefox.launch()
```

#### Issue: "Proxy connection failed"
**Symptom**: Can't connect through proxy

**Solutions**:
1. Verify proxy is working:
   ```bash
   curl --proxy socks5://proxy:port https://api.ipify.org
   ```

2. Check proxy format in config
3. Try without proxy temporarily (remove proxy_id from account)
4. Check if proxy requires authentication
5. Test with different proxy

#### Issue: "Email login fails"
**Symptom**: Can't login to email despite correct credentials

**Solutions**:
1. Check email status in logs:
   ```bash
   python cli.py logs -a 1
   ```

2. Verify email provider is supported (wp.pl, onet.pl, o2.pl, tlen.pl, interia.pl)

3. Try manual login to verify credentials

4. Check for CAPTCHA or 2FA requirements

5. Run in visible mode to see what's happening:
   ```ini
   headless_browser = false
   ```

#### Issue: "Facebook checkpoint"
**Symptom**: Facebook asks for additional verification

**Solutions**:
- This is expected for some accounts
- Status will be marked as `CHECKPOINT_REQUIRED`
- Manual intervention may be needed
- Consider using aged accounts with history

---

### Database Issues

#### Issue: "Database locked"
**Symptom**: `sqlite3.OperationalError: database is locked`

**Solutions**:
```bash
# Close all connections
pkill -f "python.*kwasny"

# Check what's using the database
lsof data/kwasny.db

# If needed, backup and recreate
cp data/kwasny.db data/kwasny_backup.db
rm data/kwasny.db
python cli.py init
```

#### Issue: "Corrupted database"
**Symptom**: Database errors or inconsistent data

**Solutions**:
```bash
# Check database integrity
sqlite3 data/kwasny.db "PRAGMA integrity_check"

# Dump and restore
sqlite3 data/kwasny.db .dump > backup.sql
rm data/kwasny.db
sqlite3 data/kwasny.db < backup.sql

# If all else fails, start fresh
rm data/kwasny.db
python cli.py init
```

---

### GUI Issues

#### Issue: "GUI won't start"
**Symptom**: `python -m src.gui.admin_panel` fails

**Solutions**:
```bash
# Check PyQt6 installation
pip install --upgrade PyQt6

# Try running directly
python src/gui/admin_panel.py

# Check for Qt platform plugin error
export QT_DEBUG_PLUGINS=1
python -m src.gui.admin_panel
```

#### Issue: "GUI freezes"
**Symptom**: GUI becomes unresponsive during processing

**Solutions**:
- This is expected during operations
- Worker thread is processing
- Wait for operation to complete
- Check console for errors
- Consider using CLI for batch operations

---

### Performance Issues

#### Issue: "System is slow"
**Symptom**: Operations take too long

**Solutions**:
1. Reduce parallel accounts:
   ```ini
   max_parallel_accounts = 2
   ```

2. Increase system resources (RAM, CPU)

3. Use faster proxies

4. Optimize for headless mode:
   ```ini
   headless_browser = true
   ```

5. Process accounts sequentially instead of parallel

#### Issue: "High memory usage"
**Symptom**: System uses too much RAM

**Solutions**:
```bash
# Process fewer accounts in parallel
# Edit config/system_settings.ini
max_parallel_accounts = 1

# Close unused browser instances
# Restart system between batches
```

---

## ❓ Frequently Asked Questions

### General Questions

**Q: Can I run this system 24/7?**
A: Yes, but it's recommended to schedule specific times for operations and monitoring.

**Q: How many accounts can I manage?**
A: Theoretically unlimited, but practical limits depend on your proxies and system resources. Start with 10-20 accounts.

**Q: Do I need one proxy per account?**
A: Yes, absolutely. This is a core security feature. Never share proxies between accounts.

**Q: What happens if a proxy fails?**
A: The system will automatically rotate to a new proxy if `auto_rotate_proxy_on_failure = true`.

**Q: Can I use free proxies?**
A: Not recommended. Free proxies are unreliable and may be blacklisted. Use paid, quality proxies.

### Configuration Questions

**Q: How do I add more email providers?**
A: Edit `config/domains_mapping.json` and add selectors in `src/modules/email_automation.py`.

**Q: Can I change financial parameters per account?**
A: Yes, use the database or API to set custom values per account.

**Q: What's the best activity percentage to use?**
A: Start with 85% and adjust based on your actual account activity.

**Q: Should I run browser in headless mode?**
A: Yes for production, no for debugging. Headless is faster and uses less resources.

### Security Questions

**Q: Is my data safe?**
A: Yes, if you:
   - Don't commit config files to git
   - Use strong passwords
   - Keep database backups secure
   - Use quality proxies

**Q: Can platforms detect this automation?**
A: Anti-detection measures are built-in, but:
   - Use quality proxies
   - Don't overuse accounts
   - Respect rate limits
   - Vary timing

**Q: What about 2FA?**
A: System will detect 2FA and mark account accordingly. Manual intervention needed.

**Q: How often should I run security scans?**
A: Daily is recommended. Configure in `system_settings.ini`.

### Financial Questions

**Q: Are the profit calculations accurate?**
A: They're estimates based on your configured costs and revenues. Adjust values to match reality.

**Q: How do I track actual vs. estimated profit?**
A: Compare calculated profits with your actual earnings and adjust `daily_revenue` parameter.

**Q: What if an account is losing money?**
A: Review the financial summary. Consider:
   - Cheaper proxy
   - Better account quality
   - Deactivating the account

**Q: How is amortization calculated?**
A: Total account/email cost divided by amortization days (default 30).

### Operational Questions

**Q: Can I pause processing?**
A: Not currently implemented. You can close the program, but active operations will be interrupted.

**Q: How do I export data?**
A: Use database queries or implement custom export in the reporting module.

**Q: Can I run multiple instances?**
A: Not recommended. Database locking may occur. Use one instance with parallel processing.

**Q: What's the recommended schedule?**
A: Daily processing during off-peak hours (e.g., 2 AM local time).

---

## 🐛 Debug Mode

### Enable Verbose Logging

Add to your script:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Run in Visible Browser Mode

Edit `config/system_settings.ini`:
```ini
headless_browser = false
```

### Check Database Contents

```bash
# View accounts
sqlite3 data/kwasny.db "SELECT * FROM accounts"

# View logs
sqlite3 data/kwasny.db "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 10"

# View financial data
sqlite3 data/kwasny.db "SELECT * FROM financial_data"
```

### Test Individual Components

```bash
# Test database
python -c "from src.database import Database; db = Database(); print('OK')"

# Test proxy parsing
python -c "from src.modules.proxy_manager import ProxyManager; pm = ProxyManager(None); print(pm.parse_proxy_url('socks5://test:test@1.1.1.1:1080'))"

# Test config loading
python -c "from src.utils.config_loader import ConfigLoader; cl = ConfigLoader(); print(cl.load_system_settings())"
```

---

## 📞 Getting Help

### Self-Help Resources

1. **Check Logs**: `python cli.py logs`
2. **Run Tests**: `python test_system.py`
3. **Read Documentation**: `README.md`, `QUICKSTART.md`, `ARCHITECTURE.md`
4. **Check Source**: Look at docstrings and comments in code

### Debug Checklist

- [ ] Dependencies installed? (`pip install -r requirements.txt`)
- [ ] Playwright installed? (`playwright install chromium`)
- [ ] Config files exist? (`config/proxies.txt`, `config/accounts.txt`)
- [ ] Database initialized? (`python cli.py init`)
- [ ] Proxies working? (Test manually with curl)
- [ ] Internet connection OK?
- [ ] Disk space available?
- [ ] Correct Python version? (3.10+)

### Report Issues

When reporting issues, include:
1. Python version (`python --version`)
2. Operating system
3. Error message (full traceback)
4. Steps to reproduce
5. Relevant log entries
6. Configuration (without sensitive data)

---

## 💡 Tips and Tricks

### Performance Tips

1. Use SSD for database
2. Close other applications
3. Use quality proxies
4. Process during off-peak hours
5. Monitor system resources

### Security Tips

1. Use unique proxies per account
2. Rotate proxies regularly
3. Don't overuse accounts
4. Monitor for blocks
5. Keep software updated

### Maintenance Tips

1. Backup database weekly
2. Review logs daily
3. Update financial configs monthly
4. Test proxies regularly
5. Archive old logs

### Development Tips

1. Test with 1-2 accounts first
2. Use visible browser for debugging
3. Check logs after each operation
4. Validate configurations before running
5. Keep development and production separate

---

**Last Updated**: 2026-02-02  
**Version**: 1.0.0
