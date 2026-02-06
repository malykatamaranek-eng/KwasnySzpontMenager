#!/usr/bin/env python
"""Quick test script to verify core functionality."""
import sys
import asyncio

print("Testing imports...")

try:
    # Test core modules
    from src.core.config import settings
    print("✓ Core config loaded")
    
    from src.core.security import encrypt_password, decrypt_password
    print("✓ Security module loaded")
    
    # Test database models
    from src.db.models import Account, Proxy, Session, AccountLog
    print("✓ Database models loaded")
    
    # Test modules
    from src.modules.proxy_manager.manager import ProductionProxyManager
    print("✓ Proxy manager loaded")
    
    from src.modules.email_discovery.detector import LiveEmailDiscovery
    print("✓ Email discovery loaded")
    
    from src.modules.auth_validator.validator import AccountValidator
    print("✓ Auth validator loaded")
    
    from src.modules.email_processor.imap_client import AsyncIMAPProcessor
    print("✓ IMAP processor loaded")
    
    from src.modules.facebook_automation.two_fa_handler import FacebookTwoFactorHandler
    print("✓ Facebook 2FA handler loaded")
    
    from src.modules.facebook_automation.reset_password import FacebookPasswordResetter
    print("✓ Password resetter loaded")
    
    # Test task system
    from src.task_system.celery_app import celery_app
    print("✓ Celery app loaded")
    
    # Test API
    from src.main import app
    print("✓ FastAPI app loaded")
    
    # Test encryption/decryption
    test_password = "test_password_123"
    encrypted = encrypt_password(test_password)
    decrypted = decrypt_password(encrypted)
    assert decrypted == test_password, "Encryption/decryption test failed"
    print("✓ Encryption/decryption working")
    
    print("\n✅ All imports successful!")
    print(f"\nApp name: {settings.APP_NAME}")
    print(f"App version: {settings.APP_VERSION}")
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"Redis URL: {settings.REDIS_URL}")
    
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
