"""Tests for security utilities — session manager, token vault, and content hashing."""

from __future__ import annotations

import time

import pytest
from cryptography.fernet import Fernet, InvalidToken

from mailagent.core.security import (
    SessionManager,
    TokenVault,
    compute_content_hash,
    validate_csrf,
)


class TestSessionManager:
    """Tests for the SessionManager class."""

    def test_create_and_validate_session(self) -> None:
        """A created session token can be successfully validated."""
        manager = SessionManager("a" * 32, max_age=3600)
        token = manager.create_session("user-123")

        data = manager.validate_session(token)
        assert data is not None
        assert data["user_id"] == "user-123"
        assert "sid" in data

    def test_expired_session_returns_none(self) -> None:
        """An expired session returns None from validation."""
        manager = SessionManager("a" * 32, max_age=0)
        token = manager.create_session("user-123")
        # The token is immediately expired since max_age=0
        time.sleep(0.1)

        data = manager.validate_session(token)
        assert data is None

    def test_tampered_token_returns_none(self) -> None:
        """A tampered session token returns None."""
        manager = SessionManager("a" * 32, max_age=3600)
        token = manager.create_session("user-123")
        tampered = token + "tampered"

        data = manager.validate_session(tampered)
        assert data is None

    def test_different_key_rejects_token(self) -> None:
        """A token signed with a different key is rejected."""
        manager1 = SessionManager("a" * 32, max_age=3600)
        manager2 = SessionManager("b" * 32, max_age=3600)

        token = manager1.create_session("user-123")
        data = manager2.validate_session(token)
        assert data is None


class TestCsrfValidation:
    """Tests for CSRF origin validation."""

    def test_valid_origin_accepted(self) -> None:
        """A matching origin is accepted."""
        assert validate_csrf("http://localhost:3000", ["http://localhost:3000"]) is True

    def test_invalid_origin_rejected(self) -> None:
        """A non-matching origin is rejected."""
        assert validate_csrf("http://evil.com", ["http://localhost:3000"]) is False

    def test_none_origin_rejected(self) -> None:
        """A missing origin is rejected."""
        assert validate_csrf(None, ["http://localhost:3000"]) is False


class TestTokenVault:
    """Tests for the MultiFernet token vault."""

    def _generate_key(self) -> str:
        return Fernet.generate_key().decode()

    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Encrypted data can be decrypted back to plaintext."""
        key = self._generate_key()
        vault = TokenVault([key])

        ciphertext = vault.encrypt("my-refresh-token")
        plaintext = vault.decrypt(ciphertext)

        assert plaintext == "my-refresh-token"
        assert ciphertext != "my-refresh-token"

    def test_key_rotation_decrypt(self) -> None:
        """Data encrypted with an old key is decryptable after adding a new key."""
        old_key = self._generate_key()
        new_key = self._generate_key()

        old_vault = TokenVault([old_key])
        ciphertext = old_vault.encrypt("my-token")

        # New vault with both keys (new first for encryption, old for decryption)
        new_vault = TokenVault([new_key, old_key])
        plaintext = new_vault.decrypt(ciphertext)

        assert plaintext == "my-token"

    def test_rotate_reencrypts_with_primary(self) -> None:
        """rotate() re-encrypts with the current primary key."""
        old_key = self._generate_key()
        new_key = self._generate_key()

        old_vault = TokenVault([old_key])
        ciphertext = old_vault.encrypt("my-token")

        new_vault = TokenVault([new_key, old_key])
        rotated = new_vault.rotate(ciphertext)

        # The rotated ciphertext should be decryptable with only the new key
        newest_vault = TokenVault([new_key])
        plaintext = newest_vault.decrypt(rotated)
        assert plaintext == "my-token"

    def test_removed_key_fails_decrypt(self) -> None:
        """Decryption fails after removing the key used for encryption."""
        old_key = self._generate_key()
        new_key = self._generate_key()

        old_vault = TokenVault([old_key])
        ciphertext = old_vault.encrypt("my-token")

        # Only new key — old key removed
        new_only_vault = TokenVault([new_key])
        with pytest.raises(InvalidToken):
            new_only_vault.decrypt(ciphertext)

    def test_empty_keys_raises_error(self) -> None:
        """TokenVault raises ValueError when initialized with no keys."""
        with pytest.raises(ValueError, match="At least one encryption key"):
            TokenVault([])


class TestContentHash:
    """Tests for the content hash function used in draft approval."""

    def test_hash_deterministic(self) -> None:
        """Same input produces same hash."""
        h1 = compute_content_hash("Re: Hello", "Thanks for the update")
        h2 = compute_content_hash("Re: Hello", "Thanks for the update")
        assert h1 == h2

    def test_hash_changes_on_body_edit(self) -> None:
        """Different body produces different hash."""
        h1 = compute_content_hash("Re: Hello", "Thanks for the update")
        h2 = compute_content_hash("Re: Hello", "Thanks for the update!")
        assert h1 != h2

    def test_hash_changes_on_subject_edit(self) -> None:
        """Different subject produces different hash."""
        h1 = compute_content_hash("Re: Hello", "body")
        h2 = compute_content_hash("Re: Hi", "body")
        assert h1 != h2

    def test_hash_is_hex_sha256(self) -> None:
        """Hash output is a 64-character hex string (SHA-256)."""
        h = compute_content_hash("subject", "body")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)
