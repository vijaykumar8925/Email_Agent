"""Security utilities: session management, CSRF protection, and token encryption.

Token encryption uses MultiFernet to support key rotation: new tokens are
encrypted with the first key, and decryption tries all keys in order.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from mailagent.core.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages session creation, validation, and destruction.

    Sessions are signed with itsdangerous using the app secret key.
    The session ID is stored in an httpOnly, Secure, SameSite=Lax cookie.
    """

    def __init__(self, secret_key: str, max_age: int = 86400) -> None:
        """Initialize the session manager.

        Args:
            secret_key: Application secret used to sign session tokens.
            max_age: Maximum session age in seconds (default: 24 hours).
        """
        self._serializer = URLSafeTimedSerializer(secret_key)
        self._max_age = max_age

    def create_session(self, user_id: str) -> str:
        """Create a signed session token for the given user.

        Args:
            user_id: The user's UUID string.

        Returns:
            A signed session token string.
        """
        session_data: dict[str, str] = {
            "user_id": user_id,
            "sid": secrets.token_hex(16),
        }
        token: str = self._serializer.dumps(session_data)
        return token

    def validate_session(self, token: str) -> dict[str, Any] | None:
        """Validate a session token and return the session data.

        Args:
            token: The signed session token from the cookie.

        Returns:
            Session data dict if valid, None if expired or tampered.
        """
        if self._max_age <= 0:
            return None
        try:
            data: dict[str, Any] = self._serializer.loads(token, max_age=self._max_age)
            return data
        except SignatureExpired:
            logger.info("session_expired")
            return None
        except BadSignature:
            logger.warning("session_invalid_signature")
            return None


def validate_csrf(origin: str | None, allowed_origins: list[str]) -> bool:
    """Validate CSRF by checking the Origin header against allowed origins.

    State-changing requests must include an Origin header matching one of
    the allowed origins. This is combined with a custom X-CSRF-Token header
    requirement for defense in depth.

    Args:
        origin: The Origin header value from the request.
        allowed_origins: List of allowed origin URLs.

    Returns:
        True if the origin is valid, False otherwise.
    """
    if origin is None:
        return False
    return origin in allowed_origins


class TokenVault:
    """Encrypts and decrypts tokens using MultiFernet for key rotation.

    The first key in the list is used for encryption. All keys are tried
    during decryption, enabling seamless key rotation: add the new key
    first, re-encrypt at your convenience, then remove the old key.
    """

    def __init__(self, keys: list[str]) -> None:
        """Initialize the token vault with encryption keys.

        Args:
            keys: List of base64-encoded Fernet keys. The first key is
                used for encryption; all are tried for decryption.

        Raises:
            ValueError: If no keys are provided.
        """
        if not keys:
            raise ValueError("At least one encryption key is required for the token vault")
        fernet_keys = [Fernet(key) for key in keys]
        self._multi_fernet = MultiFernet(fernet_keys)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string (e.g., a refresh token).

        Args:
            plaintext: The string to encrypt.

        Returns:
            Base64-encoded ciphertext string.
        """
        return self._multi_fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a ciphertext string back to plaintext.

        Args:
            ciphertext: Base64-encoded ciphertext from encrypt().

        Returns:
            The original plaintext string.

        Raises:
            InvalidToken: If decryption fails with all keys (token was
                encrypted with a key that has been removed, or is corrupted).
        """
        try:
            return self._multi_fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            logger.error("token_decryption_failed")
            raise

    def rotate(self, ciphertext: str) -> str:
        """Re-encrypt a ciphertext with the current primary key.

        Useful during key rotation: decrypt with any valid key, then
        re-encrypt with the newest key.

        Args:
            ciphertext: Existing ciphertext to re-encrypt.

        Returns:
            Ciphertext encrypted with the current primary key.
        """
        return self._multi_fernet.rotate(ciphertext.encode()).decode()


def compute_content_hash(subject: str, body: str) -> str:
    """Compute SHA-256 hash of draft content for approval verification.

    This hash is stored at approval time and re-verified before sending
    to ensure the content has not been modified after approval.

    Args:
        subject: The draft subject line.
        body: The draft body text.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    content = f"{subject}\n---\n{body}"
    return hashlib.sha256(content.encode()).hexdigest()
