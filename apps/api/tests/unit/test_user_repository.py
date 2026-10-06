"""Unit tests for UserRepository methods including get_oauth_credential."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from mailagent.users.models import OAuthCredential, User
from mailagent.users.repository import UserRepository


class TestUserRepository:
    """Test suite for UserRepository database operations."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def repo(self, mock_session: AsyncMock) -> UserRepository:
        return UserRepository(session=mock_session)

    async def test_get_oauth_credential_found(
        self,
        repo: UserRepository,
        mock_session: AsyncMock,
    ) -> None:
        user_id = uuid.uuid4()
        fake_cred = OAuthCredential(
            id=uuid.uuid4(),
            user_id=user_id,
            encrypted_access_token="enc_token",
            encrypted_refresh_token="enc_refresh",
            scopes="https://www.googleapis.com/auth/gmail.readonly",
            token_type="Bearer",
            expires_at=datetime.now(UTC),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_cred
        mock_session.execute.return_value = mock_result

        result = await repo.get_oauth_credential(user_id)
        assert result is fake_cred
        assert result.user_id == user_id
        mock_session.execute.assert_called_once()

    async def test_get_oauth_credential_not_found(
        self,
        repo: UserRepository,
        mock_session: AsyncMock,
    ) -> None:
        user_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_oauth_credential(user_id)
        assert result is None

    async def test_upsert_oauth_credential_insert_new(
        self,
        repo: UserRepository,
        mock_session: AsyncMock,
    ) -> None:
        user_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        cred = await repo.upsert_oauth_credential(
            user_id=user_id,
            encrypted_access_token="new_enc_access",
            encrypted_refresh_token="new_enc_refresh",
            scopes="https://www.googleapis.com/auth/gmail.modify",
            expires_at=None,
        )
        assert cred.user_id == user_id
        assert cred.encrypted_access_token == "new_enc_access"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    async def test_get_by_id(
        self,
        repo: UserRepository,
        mock_session: AsyncMock,
    ) -> None:
        user_id = uuid.uuid4()
        fake_user = User(
            id=user_id,
            email="test@example.com",
            google_sub="sub-12345",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_user
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_id(user_id)
        assert result is fake_user
        assert result.email == "test@example.com"
