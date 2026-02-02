#!/bin/bash
# Setup script for KWASNY LOG MANAGER

echo "🔧 KWASNY LOG MANAGER - Setup"
echo "=============================="

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "  Found: Python $python_version"

# Create virtual environment (optional but recommended)
echo ""
echo "📦 Would you like to create a virtual environment? (recommended)"
read -p "Create venv? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "  Creating virtual environment..."
    python3 -m venv venv
    echo "  ✅ Virtual environment created"
    echo "  To activate: source venv/bin/activate (Linux/Mac) or venv\\Scripts\\activate (Windows)"
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo ""
echo "🌐 Installing Playwright browsers..."
playwright install chromium

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p data logs reports

# Check for config files
echo ""
echo "📝 Checking configuration files..."
if [ ! -f config/proxies.txt ]; then
    echo "  ⚠️  config/proxies.txt not found"
    echo "     Copy config/proxies.txt.example and add your proxies"
fi

if [ ! -f config/accounts.txt ]; then
    echo "  ⚠️  config/accounts.txt not found"
    echo "     Copy config/accounts.txt.example and add your accounts"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy and configure config files:"
echo "   cp config/proxies.txt.example config/proxies.txt"
echo "   cp config/accounts.txt.example config/accounts.txt"
echo "2. Edit the config files with your data"
echo "3. Run the application:"
echo "   python -m src.gui.admin_panel  (GUI)"
echo "   python -m src.main             (CLI)"
