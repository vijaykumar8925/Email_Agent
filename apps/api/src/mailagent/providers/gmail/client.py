"""Gmail API client handling authenticated OAuth calls, message parsing, and sending."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage as MIMEEmailMessage
from typing import Any

import httpx

from mailagent.core.config import Settings, get_settings
from mailagent.core.errors import ExternalServiceError
from mailagent.core.logging import get_logger
from mailagent.core.security import TokenVault
from mailagent.users.models import OAuthCredential
from mailagent.users.repository import UserRepository

logger = get_logger(__name__)

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class ParsedEmail:
    """Extracted and decoded email message attributes."""

    def __init__(
        self,
        gmail_message_id: str,
        gmail_thread_id: str,
        sender: str,
        recipient: str,
        subject: str,
        snippet: str,
        body_text: str,
        body_html: str | None,
        received_at: datetime,
        labels: list[str],
    ) -> None:
        self.gmail_message_id = gmail_message_id
        self.gmail_thread_id = gmail_thread_id
        self.sender = sender
        self.recipient = recipient
        self.subject = subject
        self.snippet = snippet
        self.body_text = body_text
        self.body_html = body_html
        self.received_at = received_at
        self.labels = labels


def _decode_body_part(data_str: str) -> str:
    """Safely decode base64url Gmail payload."""
    try:
        # Gmail uses URL-safe base64 without padding
        padded = data_str + "=" * (-len(data_str) % 4)
        raw_bytes = base64.urlsafe_b64decode(padded)
        return raw_bytes.decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_bodies_from_payload(payload: dict[str, Any]) -> tuple[str, str | None]:
    """Recursively extract plain text and HTML from MIME payload structure."""
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    text_parts: list[str] = []
    html_parts: list[str] = []

    if body_data:
        decoded = _decode_body_part(body_data)
        if "text/plain" in mime_type:
            text_parts.append(decoded)
        elif "text/html" in mime_type:
            html_parts.append(decoded)

    # Recurse parts
    for part in payload.get("parts", []):
        sub_text, sub_html = extract_bodies_from_payload(part)
        if sub_text:
            text_parts.append(sub_text)
        if sub_html:
            html_parts.append(sub_html)

    body_text = "\n\n".join(text_parts).strip()
    body_html = "\n".join(html_parts).strip() if html_parts else None
    return body_text, body_html


class GmailClient:
    """Async client for Gmail REST API with automatic OAuth token rotation."""

    def __init__(
        self,
        credential: OAuthCredential,
        token_vault: TokenVault,
        user_repo: UserRepository,
        settings: Settings | None = None,
    ) -> None:
        self._credential = credential
        self._token_vault = token_vault
        self._user_repo = user_repo
        self._settings = settings or get_settings()

    async def get_valid_access_token(self) -> str:
        """Return a valid decrypted access token, automatically refreshing if expired."""
        now = datetime.now(UTC)
        is_expired = (
            self._credential.expires_at is None
            or self._credential.expires_at <= now + timedelta(seconds=60)
        )

        if not is_expired:
            return self._token_vault.decrypt(self._credential.encrypted_access_token)

        # Refresh token
        if not self._credential.encrypted_refresh_token:
            # Fall back to decrypting whatever access token we have
            return self._token_vault.decrypt(self._credential.encrypted_access_token)

        refresh_token = self._token_vault.decrypt(self._credential.encrypted_refresh_token)

        logger.info("refreshing_google_access_token", user_id=str(self._credential.user_id))

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self._settings.google_client_id,
                    "client_secret": self._settings.google_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            if resp.status_code != 200:
                logger.error(
                    "google_token_refresh_failed",
                    status_code=resp.status_code,
                    body=resp.text[:300],
                )
                raise ExternalServiceError(f"Failed to refresh Google token: {resp.text[:200]}")

            tokens = resp.json()
            new_access_token = tokens["access_token"]
            expires_in = tokens.get("expires_in", 3600)
            new_expires_at = now + timedelta(seconds=expires_in)

            # Re-encrypt and persist
            enc_access = self._token_vault.encrypt(new_access_token)
            await self._user_repo.upsert_oauth_credential(
                user_id=self._credential.user_id,
                encrypted_access_token=enc_access,
                encrypted_refresh_token=self._credential.encrypted_refresh_token,
                token_type="Bearer",
                scopes=self._credential.scopes,
                expires_at=new_expires_at,
            )
            self._credential.encrypted_access_token = enc_access
            self._credential.expires_at = new_expires_at

            logger.info("google_access_token_refreshed_successfully", user_id=str(self._credential.user_id))
            return new_access_token

    async def list_messages(
        self,
        query: str = "label:INBOX",
        max_results: int = 15,
    ) -> list[dict[str, str]]:
        """List messages matching query from user inbox."""
        token = await self.get_valid_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": query, "maxResults": str(max_results)}

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{GMAIL_API_BASE}/messages", headers=headers, params=params)
            if resp.status_code != 200:
                raise ExternalServiceError(f"Gmail list messages failed: {resp.status_code} - {resp.text[:200]}")

            data = resp.json()
            return data.get("messages", [])

    async def get_message(self, message_id: str) -> dict[str, Any]:
        """Fetch full details for an individual Gmail message."""
        token = await self.get_valid_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        params = {"format": "full"}

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{GMAIL_API_BASE}/messages/{message_id}", headers=headers, params=params)
            if resp.status_code != 200:
                raise ExternalServiceError(f"Gmail get message {message_id} failed: {resp.status_code}")

            return resp.json()

    def parse_message(self, raw_msg: dict[str, Any]) -> ParsedEmail:
        """Parse raw Gmail API message dict into structured ParsedEmail object."""
        msg_id = raw_msg["id"]
        thread_id = raw_msg.get("threadId", msg_id)
        snippet = raw_msg.get("snippet", "")
        labels = raw_msg.get("labelIds", [])

        # Parse headers
        headers_list = raw_msg.get("payload", {}).get("headers", [])
        headers = {h.get("name", "").lower(): h.get("value", "") for h in headers_list}

        subject = headers.get("subject", "(No Subject)")
        sender = headers.get("from", "unknown")
        recipient = headers.get("to", "")

        # Parse date
        internal_date_ms = raw_msg.get("internalDate")
        if internal_date_ms:
            received_at = datetime.fromtimestamp(int(internal_date_ms) / 1000.0, tz=UTC)
        else:
            received_at = datetime.now(UTC)

        # Extract bodies
        payload = raw_msg.get("payload", {})
        body_text, body_html = extract_bodies_from_payload(payload)

        # Fallback to snippet if body text empty
        if not body_text:
            body_text = snippet

        return ParsedEmail(
            gmail_message_id=msg_id,
            gmail_thread_id=thread_id,
            sender=sender,
            recipient=recipient,
            subject=subject,
            snippet=snippet,
            body_text=body_text,
            body_html=body_html,
            received_at=received_at,
            labels=labels,
        )

    async def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Construct RFC 5322 MIME message and dispatch via Gmail API."""
        token = await self.get_valid_access_token()

        msg = MIMEEmailMessage()
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        raw_bytes = msg.as_bytes()
        raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")

        payload: dict[str, Any] = {"raw": raw_b64}
        if thread_id:
            payload["threadId"] = thread_id

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(f"{GMAIL_API_BASE}/messages/send", headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error("gmail_send_failed", status_code=resp.status_code, body=resp.text[:300])
                raise ExternalServiceError(f"Gmail send message failed: {resp.status_code} - {resp.text[:200]}")

            return resp.json()
