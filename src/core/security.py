"""Security utilities for encryption and decryption."""
import os
import base64
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.core.exceptions import EncryptionError
from src.core.config import settings


def get_encryption_key() -> bytes:
    """Get the encryption key from settings."""
    try:
        # Try to decode as base64
        return base64.b64decode(settings.ENCRYPTION_KEY)
    except Exception:
        # If not base64, use as is (pad or trim to 32 bytes)
        key = settings.ENCRYPTION_KEY.encode()
        if len(key) < 32:
            key = key.ljust(32, b'0')
        elif len(key) > 32:
            key = key[:32]
        return key


def encrypt_password(password: str) -> bytes:
    """
    Encrypt password using AES-256-GCM.
    
    Args:
        password: Plain text password to encrypt
        
    Returns:
        Encrypted password with nonce prepended (nonce + ciphertext)
        
    Raises:
        EncryptionError: If encryption fails
    """
    try:
        key = get_encryption_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, password.encode('utf-8'), None)
        return nonce + ciphertext
    except Exception as e:
        raise EncryptionError(f"Failed to encrypt password: {str(e)}")


def decrypt_password(encrypted_password: bytes) -> str:
    """
    Decrypt password using AES-256-GCM.
    
    Args:
        encrypted_password: Encrypted password with nonce prepended
        
    Returns:
        Decrypted plain text password
        
    Raises:
        EncryptionError: If decryption fails
    """
    try:
        key = get_encryption_key()
        aesgcm = AESGCM(key)
        nonce = encrypted_password[:12]
        ciphertext = encrypted_password[12:]
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')
    except Exception as e:
        raise EncryptionError(f"Failed to decrypt password: {str(e)}")


def generate_encryption_key() -> str:
    """
    Generate a new encryption key for AES-256-GCM.
    
    Returns:
        Base64 encoded encryption key
    """
    key = AESGCM.generate_key(bit_length=256)
    return base64.b64encode(key).decode('utf-8')
