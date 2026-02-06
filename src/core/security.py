"""Security utilities for the Facebook automation system.

This module provides encryption, password hashing, and secure session
management utilities using industry-standard cryptographic libraries.
"""

import base64
import hashlib
import secrets
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.core.config import settings
from src.core.exceptions import ValidationException


class EncryptionManager:
    """Manager for encrypting and decrypting sensitive data.
    
    Uses Fernet symmetric encryption (based on AES-128-CBC) to securely
    encrypt sensitive information like passwords and tokens.
    
    Note: The encryption key should be a properly formatted Fernet key
    (32 bytes, base64-encoded). Use generate_encryption_key() to create one.
    """
    
    def __init__(self, encryption_key: Optional[str] = None) -> None:
        """Initialize encryption manager.
        
        Args:
            encryption_key: Base64-encoded Fernet key. If not provided,
                uses key from settings.
        
        Raises:
            ValidationException: If encryption key is invalid.
        """
        key = encryption_key or settings.encryption_key
        try:
            # Try to use the key directly as a Fernet key
            if len(key) == 44 and key.endswith('='):
                # Looks like a proper Fernet key
                self._fernet = Fernet(key.encode())
            else:
                # Derive key from the provided material
                self._fernet = Fernet(self._derive_key(key))
        except Exception as e:
            raise ValidationException(
                field="encryption_key",
                message=f"Invalid encryption key: {str(e)}"
            )
    
    @staticmethod
    def _derive_key(key_material: str) -> bytes:
        """Derive a Fernet key from key material using application-specific salt.
        
        Uses PBKDF2 to derive a proper 32-byte key from the provided
        key material. The salt is application-specific to ensure consistent
        key derivation from the same key material.
        
        Warning: This is a fallback for non-standard keys. For production,
        use a properly generated Fernet key via generate_encryption_key().
        
        Args:
            key_material: The source key material (password/secret).
        
        Returns:
            bytes: A properly formatted Fernet key.
        """
        # Use app-specific salt for consistent key derivation
        app_salt = hashlib.sha256(b"facebook_automation_system_v1").digest()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=app_salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_material.encode()))
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string.
        
        Args:
            plaintext: The string to encrypt.
        
        Returns:
            str: Base64-encoded encrypted string.
        
        Raises:
            ValidationException: If encryption fails.
        """
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            raise ValidationException(
                field="plaintext",
                message=f"Encryption failed: {str(e)}"
            )
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext string.
        
        Args:
            ciphertext: The base64-encoded encrypted string.
        
        Returns:
            str: The decrypted plaintext.
        
        Raises:
            ValidationException: If decryption fails or token is invalid.
        """
        try:
            decrypted_bytes = self._fernet.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except InvalidToken:
            raise ValidationException(
                field="ciphertext",
                message="Invalid or corrupted ciphertext"
            )
        except Exception as e:
            raise ValidationException(
                field="ciphertext",
                message=f"Decryption failed: {str(e)}"
            )
    
    def encrypt_dict(self, data: dict[str, str]) -> dict[str, str]:
        """Encrypt all values in a dictionary.
        
        Args:
            data: Dictionary with string values to encrypt.
        
        Returns:
            dict: Dictionary with encrypted values.
        """
        return {key: self.encrypt(value) for key, value in data.items()}
    
    def decrypt_dict(self, data: dict[str, str]) -> dict[str, str]:
        """Decrypt all values in a dictionary.
        
        Args:
            data: Dictionary with encrypted string values.
        
        Returns:
            dict: Dictionary with decrypted values.
        """
        return {key: self.decrypt(value) for key, value in data.items()}


class PasswordHasher:
    """Utilities for hashing and verifying passwords.
    
    Uses PBKDF2-SHA256 for secure password hashing with configurable
    iterations and salt.
    """
    
    # Class constant for consistent iteration count
    DEFAULT_ITERATIONS = 100000
    
    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None, iterations: Optional[int] = None) -> str:
        """Hash a password using PBKDF2-SHA256.
        
        Args:
            password: The plaintext password to hash.
            salt: Optional salt bytes. If not provided, generates random salt.
            iterations: Number of PBKDF2 iterations. If not provided, uses DEFAULT_ITERATIONS.
        
        Returns:
            str: The hashed password in format 'salt:hash' (both base64-encoded).
        """
        if salt is None:
            salt = secrets.token_bytes(32)
        
        if iterations is None:
            iterations = PasswordHasher.DEFAULT_ITERATIONS
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        hash_bytes = kdf.derive(password.encode())
        
        # Encode salt and hash as base64 and combine
        salt_b64 = base64.b64encode(salt).decode()
        hash_b64 = base64.b64encode(hash_bytes).decode()
        return f"{salt_b64}:{hash_b64}"
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify a password against a hashed password.
        
        Args:
            password: The plaintext password to verify.
            hashed_password: The hashed password in format 'salt:hash'.
        
        Returns:
            bool: True if password matches, False otherwise.
        
        Raises:
            ValidationException: If hashed password format is invalid.
        """
        try:
            salt_b64, expected_hash_b64 = hashed_password.split(":", 1)
            salt = base64.b64decode(salt_b64)
            expected_hash = base64.b64decode(expected_hash_b64)
        except (ValueError, Exception) as e:
            raise ValidationException(
                field="hashed_password",
                message=f"Invalid hashed password format: {str(e)}"
            )
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=PasswordHasher.DEFAULT_ITERATIONS,
        )
        
        try:
            kdf.verify(password.encode(), expected_hash)
            return True
        except Exception:
            return False


class TokenGenerator:
    """Generate secure random tokens for sessions and verification."""
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a secure random token.
        
        Args:
            length: The length of the token in bytes (default: 32).
        
        Returns:
            str: A URL-safe base64-encoded token.
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_hex_token(length: int = 32) -> str:
        """Generate a secure random hexadecimal token.
        
        Args:
            length: The length of the token in bytes (default: 32).
        
        Returns:
            str: A hexadecimal token.
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_numeric_code(digits: int = 6) -> str:
        """Generate a secure random numeric code.
        
        Args:
            digits: Number of digits in the code (default: 6).
        
        Returns:
            str: A numeric code with leading zeros if necessary.
        """
        max_value = 10 ** digits
        code = secrets.randbelow(max_value)
        return str(code).zfill(digits)


class SessionManager:
    """Manage secure session identifiers and validation."""
    
    def __init__(self) -> None:
        """Initialize session manager."""
        self._token_generator = TokenGenerator()
    
    def create_session_id(self) -> str:
        """Create a new secure session identifier.
        
        Returns:
            str: A unique session identifier.
        """
        return self._token_generator.generate_token(32)
    
    @staticmethod
    def hash_session_id(session_id: str) -> str:
        """Hash a session ID for storage.
        
        Args:
            session_id: The session identifier to hash.
        
        Returns:
            str: SHA-256 hash of the session ID.
        """
        return hashlib.sha256(session_id.encode()).hexdigest()
    
    @staticmethod
    def validate_session_format(session_id: str) -> bool:
        """Validate session ID format.
        
        Args:
            session_id: The session identifier to validate.
        
        Returns:
            bool: True if format is valid, False otherwise.
        """
        if not session_id or not isinstance(session_id, str):
            return False
        
        # Session IDs should be URL-safe base64 strings
        try:
            # Check length (32 bytes -> ~43 chars in base64)
            if len(session_id) < 40 or len(session_id) > 50:
                return False
            
            # Check characters (alphanumeric, -, _)
            allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
            return all(c in allowed_chars for c in session_id)
        except Exception:
            return False


def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key.
    
    This is a utility function for generating new encryption keys
    for use in configuration. The generated key should be stored
    securely in environment variables.
    
    Returns:
        str: A base64-encoded Fernet key.
    """
    return Fernet.generate_key().decode()


# Global instances for convenience
encryption_manager = EncryptionManager()
password_hasher = PasswordHasher()
token_generator = TokenGenerator()
session_manager = SessionManager()
