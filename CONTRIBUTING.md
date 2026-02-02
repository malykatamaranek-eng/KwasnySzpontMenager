# Contributing to KWASNY LOG MANAGER

## 🤝 Welcome

Thank you for your interest in contributing to KWASNY LOG MANAGER! This document provides guidelines for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)

## 📜 Code of Conduct

### Our Standards

- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other community members

## 🚀 Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/KwasnySzpontMenager.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test thoroughly
6. Submit a pull request

## 🛠️ Development Setup

```bash
# Clone repository
git clone https://github.com/malykatamaranek-eng/KwasnySzpontMenager.git
cd KwasnySzpontMenager

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run tests
python test_system.py
```

## 💡 How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Description**: Clear description of the bug
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**: OS, Python version, dependencies versions
- **Logs**: Relevant log entries or error messages
- **Screenshots**: If applicable

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Use Case**: Why this enhancement would be useful
- **Description**: Clear description of the enhancement
- **Examples**: If applicable, provide examples
- **Alternatives**: Any alternative solutions you've considered

### Areas for Contribution

#### High Priority
- Additional email provider support
- Advanced reporting and analytics
- Performance optimizations
- Better error handling
- Enhanced security features

#### Medium Priority
- UI/UX improvements
- Additional export formats
- Better documentation
- Test coverage improvements
- Code refactoring

#### Low Priority
- Additional languages support
- Theme customization
- Plugin system
- API endpoints

## 📝 Coding Standards

### Python Style Guide

Follow PEP 8 with these specifics:

```python
# Imports
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Classes
class MyClass:
    """
    Brief description of class
    
    Detailed description if needed
    """
    
    def __init__(self, param: str):
        """Initialize with parameters"""
        self.param = param
    
    def my_method(self, arg: int) -> str:
        """
        Brief description of method
        
        Args:
            arg: Description of argument
            
        Returns:
            Description of return value
        """
        return f"Result: {arg}"

# Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Variables
user_name = "example"
is_active = True
```

### Documentation

- All modules must have docstrings
- All classes must have docstrings
- All public methods must have docstrings
- Include type hints where possible
- Comment complex logic

### Git Commit Messages

Format: `<type>(<scope>): <subject>`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(proxy): Add HTTP proxy support
fix(database): Fix connection leak issue
docs(readme): Update installation instructions
refactor(email): Simplify provider detection logic
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python test_system.py

# Test specific module
python -m pytest tests/test_proxy_manager.py

# Test with coverage
python -m pytest --cov=src tests/
```

### Writing Tests

```python
import pytest
from src.modules.proxy_manager import ProxyManager

def test_proxy_parsing():
    """Test proxy URL parsing"""
    pm = ProxyManager(None)
    config = pm.parse_proxy_url("socks5://user:pass@1.1.1.1:1080")
    
    assert config is not None
    assert config.host == "1.1.1.1"
    assert config.port == 1080
    assert config.username == "user"
    assert config.password == "pass"

def test_invalid_proxy():
    """Test invalid proxy URL"""
    pm = ProxyManager(None)
    config = pm.parse_proxy_url("invalid://proxy")
    
    assert config is None
```

### Test Coverage Requirements

- New features must include tests
- Bug fixes should include regression tests
- Aim for 80%+ code coverage
- Critical paths must be tested

## 🔄 Pull Request Process

### Before Submitting

1. **Update Documentation**: Update README.md, docstrings, etc.
2. **Run Tests**: Ensure all tests pass
3. **Check Style**: Follow coding standards
4. **Update Changelog**: Add your changes to CHANGELOG.md
5. **Clean Commits**: Rebase/squash if needed

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All tests pass
- [ ] Added new tests
- [ ] Tested manually

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Changes are backwards compatible (or breaking changes documented)
```

### Review Process

1. Submit PR with clear description
2. Wait for automated checks
3. Address reviewer comments
4. Make requested changes
5. Wait for approval
6. PR will be merged by maintainer

## 🏗️ Project Structure

```
src/
├── database.py              # Core database operations
├── main.py                  # Main application coordinator
├── modules/                 # Feature modules
│   ├── proxy_manager.py
│   ├── email_automation.py
│   ├── facebook_automation.py
│   ├── security_manager.py
│   └── financial_calculator.py
├── gui/                     # GUI components
│   └── admin_panel.py
└── utils/                   # Utility functions
    └── config_loader.py

config/                      # Configuration files
tests/                       # Test files
docs/                        # Additional documentation
```

## 🎯 Development Guidelines

### Adding New Email Provider

1. Add provider config to `domains_mapping.json`
2. Update `PROVIDERS` dict in `email_automation.py`
3. Add selectors for login elements
4. Add error indicators
5. Test thoroughly
6. Update documentation

### Adding New Module

1. Create file in `src/modules/`
2. Implement module class
3. Add to main coordinator
4. Write tests
5. Update documentation
6. Add example usage

### Modifying Database Schema

1. Plan migration strategy
2. Update `database.py`
3. Write migration script
4. Test with existing data
5. Update documentation

## 🐛 Debugging Tips

### Enable Debug Mode

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Common Issues

1. **Import Errors**: Check `PYTHONPATH` and module structure
2. **Database Locked**: Close all connections before testing
3. **Browser Issues**: Reinstall Playwright browsers
4. **Proxy Errors**: Test proxy manually first

## 📚 Resources

- [Python PEP 8](https://www.python.org/dev/peps/pep-0008/)
- [Playwright Documentation](https://playwright.dev/python/)
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)

## 📧 Contact

- **Issues**: [GitHub Issues](https://github.com/malykatamaranek-eng/KwasnySzpontMenager/issues)
- **Discussions**: [GitHub Discussions](https://github.com/malykatamaranek-eng/KwasnySzpontMenager/discussions)
- **Security**: Report security issues privately to maintainers

## 🙏 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project README

Thank you for contributing to KWASNY LOG MANAGER! 🎉

---

**Note**: This project is under active development. These guidelines may evolve. Always check the latest version before contributing.
